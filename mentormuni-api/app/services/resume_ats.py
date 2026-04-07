from __future__ import annotations

import asyncio
import io
import json
import logging
import re
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any, List, Optional, Set, Tuple

from openai import AsyncOpenAI
from pypdf import PdfReader

logger = logging.getLogger("resume_ats")

# LLM enrichment: resume excerpt size and response cap (scores stay heuristic).
RESUME_LLM_MAX_INPUT_CHARS = 14_000
RESUME_LLM_MAX_TOKENS = 1_600

ALLOWED_EXTENSIONS = {".pdf", ".doc", ".docx"}
MAX_FILE_BYTES = 5 * 1024 * 1024
MIN_TEXT_CHARS = 80

# Role / resume tokens to ignore when building keyword lists
_STOPWORDS = {
    "a",
    "an",
    "the",
    "and",
    "or",
    "for",
    "with",
    "to",
    "of",
    "in",
    "on",
    "at",
    "as",
    "by",
    "from",
    "into",
    "role",
    "position",
    "job",
    "seeking",
    "looking",
    "full",
    "time",
    "part",
    "remote",
    "hybrid",
    "onsite",
    "years",
    "year",
    "yrs",
    "exp",
    "experience",
    "developer",
    "engineer",
    "engineering",
    "senior",
    "junior",
    "lead",
    "staff",
    "principal",
    "intern",
    "associate",
}

# Light synonym expansion for common tech (substring match still uses word boundaries)
_KEYWORD_ALIASES: dict[str, Set[str]] = {
    "react": {"javascript", "typescript", "jsx", "redux"},
    "node": {"nodejs", "express", "npm"},
    "python": {"django", "flask", "fastapi"},
    "java": {"spring", "kotlin"},
    "aws": {"cloud", "ec2", "s3", "lambda"},
    "azure": {"devops", "kubernetes", "k8s", "docker"},
    "sql": {"mysql", "postgres", "postgresql", "database"},
    "ml": {"machine", "learning", "tensorflow", "pytorch"},
}


def _extract_pdf(content: bytes) -> str:
    reader = PdfReader(io.BytesIO(content))
    parts: List[str] = []
    for page in reader.pages:
        t = page.extract_text() or ""
        if t.strip():
            parts.append(t)
    return "\n".join(parts)


def _extract_docx(content: bytes) -> str:
    from docx import Document

    doc = Document(io.BytesIO(content))
    return "\n".join(p.text for p in doc.paragraphs if p.text and p.text.strip())


def _extract_doc_rtf(content: bytes) -> Optional[str]:
    try:
        from striprtf.striprtf import rtf_to_text
    except ImportError:
        return None
    try:
        text = content.decode("utf-8", errors="ignore")
    except Exception:
        return None
    if not text.lstrip().startswith("{\\rtf"):
        return None
    try:
        return rtf_to_text(text)
    except Exception:
        return None


def _extract_doc_antiword(content: bytes) -> Optional[str]:
    if not shutil.which("antiword"):
        return None
    try:
        with tempfile.NamedTemporaryFile(suffix=".doc", delete=False) as tmp:
            tmp.write(content)
            tmp.flush()
            path = tmp.name
        try:
            out = subprocess.run(
                ["antiword", path],
                capture_output=True,
                text=True,
                timeout=30,
                check=False,
            )
            if out.returncode == 0 and (out.stdout or "").strip():
                return out.stdout
        finally:
            Path(path).unlink(missing_ok=True)
    except Exception as e:
        logger.warning("antiword extraction failed: %s", e)
    return None


def extract_text(filename: str, content: bytes) -> str:
    if len(content) > MAX_FILE_BYTES:
        raise ValueError(f"File too large. Maximum size is {MAX_FILE_BYTES // (1024 * 1024)} MB.")

    suffix = Path(filename or "").suffix.lower()
    if suffix not in ALLOWED_EXTENSIONS:
        raise ValueError("Only PDF, DOC, and DOCX files are supported.")

    if suffix == ".pdf":
        try:
            text = _extract_pdf(content)
        except Exception as e:
            logger.exception("PDF extraction failed")
            raise ValueError("Could not read this PDF. Try another file or export as PDF again.") from e
    elif suffix == ".docx":
        try:
            text = _extract_docx(content)
        except Exception as e:
            logger.exception("DOCX extraction failed")
            raise ValueError("Could not read this DOCX file. Try saving again from Word.") from e
    else:
        text = ""
        rtf = _extract_doc_rtf(content)
        if rtf and len(rtf.strip()) >= MIN_TEXT_CHARS:
            text = rtf
        if not text.strip():
            aw = _extract_doc_antiword(content)
            if aw:
                text = aw
        if not text.strip():
            raise ValueError(
                "Could not read this .doc file. Save as .docx or PDF and upload again, "
                "or install antiword on the server for legacy Word files."
            )

    cleaned = (text or "").strip()
    if len(cleaned) < MIN_TEXT_CHARS:
        raise ValueError(
            "Very little text could be extracted. Check that the file is not image-only or password-protected."
        )
    return cleaned


def _tokenize_role(role: str) -> List[str]:
    raw = re.findall(r"[a-z0-9+#.]+", role.lower())
    terms: List[str] = []
    for t in raw:
        if len(t) < 2 or t in _STOPWORDS:
            continue
        terms.append(t)
    if re.search(r"machine\s+learning", role, re.I) and "learning" in terms and "machine" not in terms:
        terms.insert(0, "machine")
    return list(dict.fromkeys(terms))


def _word_boundary_match(haystack: str, term: str) -> bool:
    if len(term) < 2:
        return False
    try:
        return re.search(rf"(?<!\w){re.escape(term)}(?!\w)", haystack, re.IGNORECASE) is not None
    except re.error:
        return term.lower() in haystack.lower()


def _keyword_analysis(resume_lower: str, target_role: str) -> Tuple[int, List[str], List[str]]:
    primary = _tokenize_role(target_role)
    if not primary:
        primary = ["software", "engineering"]

    matched: List[str] = []
    missing: List[str] = []
    for p in primary:
        family = {p} | _KEYWORD_ALIASES.get(p, set())
        if any(_word_boundary_match(resume_lower, w) for w in family):
            matched.append(p)
        else:
            missing.append(p)

    score = int(round(100 * len(matched) / max(len(primary), 1)))
    return score, matched, missing


_SECTION_PATTERNS = (
    r"\bexperience\b",
    r"\beducation\b",
    r"\bskills?\b",
    r"\bprojects?\b",
    r"\bsummary\b",
    r"\bwork\b",
)

_ACTION_VERBS = (
    "led",
    "built",
    "designed",
    "developed",
    "implemented",
    "improved",
    "increased",
    "reduced",
    "delivered",
    "achieved",
    "owned",
    "launched",
    "scaled",
    "optimized",
    "created",
    "managed",
)


def _formatting_score(text: str) -> int:
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    score = 35
    if len(lines) >= 8:
        score += 15
    if len(lines) >= 20:
        score += 10
    joined = "\n".join(lines[:120]).lower()
    if re.search(r"[a-z0-9._%+-]+@[a-z0-9.-]+\.[a-z]{2,}", text, re.I):
        score += 12
    section_hits = sum(1 for p in _SECTION_PATTERNS if re.search(p, joined))
    score += min(18, section_hits * 4)
    bulletish = sum(1 for ln in lines if re.match(r"^[\-\u2022\u2023\*]\s+", ln) or re.match(r"^\d+[\.)]\s+", ln))
    score += min(12, bulletish * 2)
    if 400 <= len(text) <= 12000:
        score += 8
    return max(0, min(100, score))


def _impact_score(text: str) -> int:
    lower = text.lower()
    score = 30
    if re.search(r"\d+\s*%", text):
        score += 12
    if re.search(r"\$\s*\d|\d+\s*k\b|\d+\s*m\b", lower):
        score += 8
    if re.search(r"\d+\s*\+?\s*(years?|yrs?|months?)\b", lower):
        score += 10
    verb_hits = sum(1 for v in _ACTION_VERBS if re.search(rf"\b{v}\b", lower))
    score += min(30, verb_hits * 4)
    if len([ln for ln in text.splitlines() if len(ln.strip()) > 40]) >= 3:
        score += 10
    return max(0, min(100, score))


def _ats_parse_score(text: str) -> int:
    lower = text.lower()
    score = 40
    # Section signals
    if any(re.search(p, lower) for p in _SECTION_PATTERNS):
        score += 20
    # Not mostly non-letters
    letters = sum(1 for c in text if c.isalpha())
    if len(text) > 50 and letters / max(len(text), 1) > 0.45:
        score += 15
    # Contact / structure
    if re.search(r"\b(linkedin|github)\b", lower):
        score += 10
    lines = [ln for ln in text.splitlines() if ln.strip()]
    if len(lines) >= 5:
        score += 10
    return max(0, min(100, score))


def _overall(keyword: int, formatting: int, impact: int, ats: int) -> int:
    return int(round(0.35 * keyword + 0.20 * formatting + 0.25 * impact + 0.20 * ats))


def _build_summary(
    overall: int,
    kw_score: int,
    matched: List[str],
    missing: List[str],
    target_role: str,
) -> str:
    role = target_role.strip() or "your target role"
    if overall >= 80:
        tone = "strong"
    elif overall >= 60:
        tone = "moderate"
    else:
        tone = "needs improvement"
    m_preview = ", ".join(matched[:5]) if matched else "few role-specific terms"
    gap_hint = ""
    if missing:
        gap_hint = f" Consider weaving in: {', '.join(missing[:5])}."
    return (
        f"ATS-style fit for {role} looks {tone} (overall {overall}/100). "
        f"Keyword coverage includes {m_preview}.{gap_hint}"
    )


def _build_fixes(
    missing: List[str],
    formatting: int,
    impact: int,
    ats: int,
) -> List[str]:
    fixes: List[str] = []
    if missing:
        fixes.append(
            f"Add role-relevant keywords where truthful: {', '.join(missing[:8])}."
        )
    if formatting < 70:
        fixes.append(
            "Use clear section headings (Experience, Education, Skills) and consistent bullet formatting."
        )
    if impact < 65:
        fixes.append(
            "Quantify outcomes (%, revenue, latency, team size, users) next to responsibilities."
        )
    if ats < 70:
        fixes.append(
            "Ensure contact info and standard sections are easy to find; avoid tables-only layouts when possible."
        )
    if len(fixes) < 3:
        fixes.append("Tailor a one-line summary at the top to mirror the job title you are targeting.")
    return fixes[:8]


def _build_strengths(
    matched: List[str],
    formatting: int,
    impact: int,
    text: str,
) -> List[str]:
    strengths: List[str] = []
    if matched:
        strengths.append(f"Keywords aligned with the role: {', '.join(matched[:6])}.")
    if formatting >= 72:
        strengths.append("Readable structure with sections and bullets.")
    if impact >= 68:
        strengths.append("Evidence of measurable or action-oriented statements.")
    if re.search(r"[a-z0-9._%+-]+@[a-z0-9.-]+\.[a-z]{2,}", text, re.I):
        strengths.append("Contact information is present for recruiters.")
    if not strengths:
        strengths.append("Resume length is sufficient for ATS text extraction.")
    return strengths[:6]


def _default_portal_tips(missing: List[str], target_role: str) -> List[str]:
    """Baseline Naukri / LinkedIn tips when LLM is off or does not return portal_tips."""
    tr = (target_role or "").strip() or "your target role"
    tips = [
        f"Naukri: use a headline/title that closely matches “{tr}” and repeat core skills from the job family in your key skills section.",
        "Naukri: upload a text-friendly PDF or DOCX; avoid image-only CVs so keyword search can read your content.",
        "LinkedIn: align your profile headline and About with the same role title and top skills as on this resume for consistent recruiter search.",
        "LinkedIn: add the same tools and skills to your Skills section and keep work history dates aligned with the resume.",
    ]
    if missing:
        tips.append(
            "Where truthful, add these recruiter-search terms to resume skills, summary, and first experience bullet, "
            "then mirror them on Naukri key skills and LinkedIn: "
            + ", ".join(missing[:8])
            + "."
        )
    return tips[:10]


def analyze_resume(text: str, target_role: str) -> dict:
    tr = (target_role or "").strip() or "Software Developer"
    resume_lower = text.lower()
    kw_score, matched, missing = _keyword_analysis(resume_lower, tr)
    fmt = _formatting_score(text)
    imp = _impact_score(text)
    ats = _ats_parse_score(text)
    overall = _overall(kw_score, fmt, imp, ats)

    return {
        "score": overall,
        "ats": ats,
        "keywords": kw_score,
        "formatting": fmt,
        "impact": imp,
        "summary": _build_summary(overall, kw_score, matched, missing, tr),
        "matched_keywords": matched,
        "missing_keywords": missing,
        "fixes": _build_fixes(missing, fmt, imp, ats),
        "strengths": _build_strengths(matched, fmt, imp, text),
        "portal_tips": _default_portal_tips(missing, tr),
    }


def _parse_llm_coaching_json(content: str) -> Optional[dict[str, Any]]:
    content = (content or "").strip()
    if not content:
        return None
    m = re.search(r"\{[\s\S]*\}", content)
    if not m:
        return None
    try:
        obj = json.loads(m.group())
    except json.JSONDecodeError:
        return None
    if not isinstance(obj, dict):
        return None
    return obj


def _sanitize_coaching(obj: dict[str, Any]) -> Optional[dict[str, str | list[str]]]:
    out: dict[str, str | list[str]] = {}
    s = obj.get("summary")
    if isinstance(s, str) and s.strip():
        out["summary"] = s.strip()[:2000]

    fixes = obj.get("fixes")
    if isinstance(fixes, list):
        clean = []
        for x in fixes[:8]:
            if isinstance(x, str) and x.strip():
                clean.append(x.strip()[:500])
        if clean:
            out["fixes"] = clean

    strengths = obj.get("strengths")
    if isinstance(strengths, list):
        clean = []
        for x in strengths[:6]:
            if isinstance(x, str) and x.strip():
                clean.append(x.strip()[:500])
        if clean:
            out["strengths"] = clean

    portal = obj.get("portal_tips")
    if isinstance(portal, list):
        clean = []
        for x in portal[:10]:
            if isinstance(x, str) and x.strip():
                clean.append(x.strip()[:500])
        if clean:
            out["portal_tips"] = clean

    return out if out.get("summary") or out.get("fixes") or out.get("strengths") or out.get("portal_tips") else None


async def enrich_analysis_with_llm(payload: dict, resume_text: str, target_role: str) -> dict:
    """
    Rewrite summary / fixes / strengths using OpenAI. Numeric scores and matched/missing keywords
    stay from heuristics (factual). On any failure, returns payload unchanged.
    """
    from app.core.config import settings

    if not settings.resume_ats_use_llm:
        return payload

    excerpt = resume_text[:RESUME_LLM_MAX_INPUT_CHARS]
    if len(resume_text) > RESUME_LLM_MAX_INPUT_CHARS:
        excerpt += "\n\n[… resume truncated for analysis …]"

    timeout_sec = min(90, max(25, int(settings.llm_timeout_seconds)))

    snapshot = (
        f"Target role: {target_role.strip()}\n"
        f"Overall score (heuristic): {payload.get('score')}/100\n"
        f"Breakdown — keywords: {payload.get('keywords')}, formatting: {payload.get('formatting')}, "
        f"impact: {payload.get('impact')}, ATS parse: {payload.get('ats')}\n"
        f"Matched role keywords: {', '.join(payload.get('matched_keywords') or []) or '(none)'}\n"
        f"Missing role keywords: {', '.join(payload.get('missing_keywords') or []) or '(none)'}\n"
    )

    prompt = f"""You are an expert technical recruiter focused on India job portals (Naukri) and LinkedIn shortlisting.

Goal: help this candidate get MORE recruiter views and shortlists for their target role on Naukri and LinkedIn.

Use ONLY the resume excerpt and the heuristic snapshot below. Do not invent employers, degrees, or skills not present in the resume.
If the resume is thin, say so tactfully.

HEURISTIC SCORES (0–100 each — reference them explicitly in your summary so the candidate sees what the numbers mean):
- Overall shortlisting-style score: {payload.get('score')}
- Keyword match vs target role title: {payload.get('keywords')}
- Formatting / structure: {payload.get('formatting')}
- Impact (metrics, action verbs): {payload.get('impact')}
- Parseability / ATS-friendly text: {payload.get('ats')}

{snapshot}

RESUME TEXT:
---
{excerpt}
---

Return ONLY a JSON object with these keys (no markdown fences):
{{
  "summary": "4–6 sentences. MUST: (1) State the overall score and what it means for Naukri/LinkedIn visibility in plain language. (2) Mention keyword/formatting/impact briefly if useful. (3) One encouraging close.",
  "strengths": ["3–6 bullets: what is ALREADY good for recruiter search and screening on Naukri/LinkedIn"],
  "fixes": ["4–8 bullets: PRIORITIZED resume edits to improve shortlisting—most important first"],
  "portal_tips": ["5–10 bullets: concrete Naukri-specific AND LinkedIn-specific actions (headline, key skills, About, job title, PDF upload, skill endorsements, consistency between resume and profile)."]
}}

Rules:
- Ground every point in the resume text or the matched/missing keywords; use missing keywords in fixes/portal_tips where truthful.
- strengths = what to keep or double down on; fixes = resume file improvements; portal_tips = what to do on Naukri.com and LinkedIn specifically.
- Short bullet strings only; no nested objects.
"""

    async def _call() -> str:
        client = AsyncOpenAI(api_key=settings.openai_api_key)
        response = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=RESUME_LLM_MAX_TOKENS,
            temperature=0.35,
        )
        return (response.choices[0].message.content or "").strip()

    try:
        raw = await asyncio.wait_for(_call(), timeout=timeout_sec)
    except Exception as e:
        logger.warning("Resume ATS LLM enrichment failed: %s", e)
        return payload

    parsed = _parse_llm_coaching_json(raw)
    if not parsed:
        logger.warning("Resume ATS LLM returned unparseable JSON")
        return payload

    coaching = _sanitize_coaching(parsed)
    if not coaching:
        return payload

    merged = {**payload}
    if "summary" in coaching:
        merged["summary"] = coaching["summary"]
    if "fixes" in coaching:
        merged["fixes"] = coaching["fixes"]
    if "strengths" in coaching:
        merged["strengths"] = coaching["strengths"]
    if "portal_tips" in coaching:
        merged["portal_tips"] = coaching["portal_tips"]
    return merged

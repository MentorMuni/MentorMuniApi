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

from app.services.resume_ats_llm_prompt import render_resume_ats_enrich_prompt

logger = logging.getLogger("resume_ats")

# LLM enrichment: resume excerpt size and response cap (scores stay heuristic).
RESUME_LLM_MAX_INPUT_CHARS = 14_000
RESUME_LLM_MAX_TOKENS = 4_500

ALLOWED_EXTENSIONS = {".pdf", ".doc", ".docx"}
MAX_FILE_BYTES = 5 * 1024 * 1024
MIN_TEXT_CHARS = 80

# Filler tokens only — keep role-meaningful words like developer, engineer, java, react.
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
}

# Light synonym expansion for common tech (word-boundary match)
_KEYWORD_ALIASES: dict[str, Set[str]] = {
    "react": {"javascript", "typescript", "jsx", "redux"},
    "node": {"nodejs", "express", "npm"},
    "nodejs": {"node", "express", "npm"},
    "python": {"django", "flask", "fastapi"},
    "java": {"spring", "kotlin", "jvm"},
    "aws": {"cloud", "ec2", "s3", "lambda"},
    "azure": {"cloud", "devops"},
    "gcp": {"cloud", "google"},
    "sql": {"mysql", "postgres", "postgresql", "database"},
    "ml": {"machine", "learning", "tensorflow", "pytorch"},
    "devops": {"ci/cd", "docker", "kubernetes", "jenkins"},
    "frontend": {"react", "javascript", "html", "css"},
    "backend": {"api", "rest", "microservices", "database"},
}

# High-impact keywords per role family (India campus + mid-level hiring)
_ROLE_KEYWORD_BANK: dict[str, List[str]] = {
    "software engineer": [
        "java",
        "python",
        "git",
        "api",
        "sql",
        "agile",
        "testing",
        "debugging",
        "oop",
        "data structures",
    ],
    "frontend": [
        "react",
        "javascript",
        "typescript",
        "html",
        "css",
        "responsive",
        "rest",
        "git",
        "redux",
        "webpack",
    ],
    "backend": [
        "java",
        "spring",
        "api",
        "sql",
        "microservices",
        "rest",
        "database",
        "linux",
        "docker",
        "kafka",
    ],
    "full stack": [
        "react",
        "node",
        "javascript",
        "sql",
        "api",
        "rest",
        "git",
        "mongodb",
        "express",
        "aws",
    ],
    "java": [
        "java",
        "spring",
        "hibernate",
        "sql",
        "rest",
        "maven",
        "junit",
        "microservices",
        "kafka",
        "multithreading",
    ],
    "python": [
        "python",
        "django",
        "flask",
        "fastapi",
        "sql",
        "api",
        "pandas",
        "git",
        "testing",
        "rest",
    ],
    "data analyst": [
        "sql",
        "excel",
        "python",
        "tableau",
        "power bi",
        "statistics",
        "visualization",
        "dashboard",
        "analytics",
        "reporting",
    ],
    "data scientist": [
        "python",
        "machine learning",
        "sql",
        "pandas",
        "tensorflow",
        "pytorch",
        "statistics",
        "nlp",
        "scikit-learn",
        "deep learning",
    ],
    "devops": [
        "docker",
        "kubernetes",
        "aws",
        "ci/cd",
        "linux",
        "terraform",
        "jenkins",
        "ansible",
        "monitoring",
        "git",
    ],
    "android": [
        "kotlin",
        "java",
        "android",
        "rest",
        "sqlite",
        "mvvm",
        "firebase",
        "git",
        "api",
        "gradle",
    ],
    "qa": [
        "selenium",
        "testing",
        "automation",
        "api",
        "junit",
        "testng",
        "agile",
        "bug",
        "regression",
        "jenkins",
    ],
    "business analyst": [
        "requirements",
        "sql",
        "excel",
        "jira",
        "stakeholder",
        "documentation",
        "agile",
        "uml",
        "process",
        "analytics",
    ],
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


def _role_bank_keywords(target_role: str) -> List[str]:
    """Pick the best keyword bank entry for the target role label."""
    tr = (target_role or "").lower()
    best: List[str] = []
    best_len = 0
    for key, kws in _ROLE_KEYWORD_BANK.items():
        if key in tr and len(key) > best_len:
            best = kws
            best_len = len(key)
    return list(best)


def _jd_keywords(job_description: str, max_terms: int = 12) -> List[str]:
    """Extract searchable terms from an optional job description."""
    if not (job_description or "").strip():
        return []
    raw = re.findall(r"[a-z0-9+#./-]+", job_description.lower())
    terms: List[str] = []
    for t in raw:
        if len(t) < 2 or t in _STOPWORDS:
            continue
        if t.isdigit():
            continue
        terms.append(t)
    # Prefer longer / less common tokens first for JD-specific skills
    unique = list(dict.fromkeys(terms))
    return unique[:max_terms]


def _build_keyword_targets(target_role: str, job_description: Optional[str] = None) -> List[str]:
    """Merge role tokens, role-bank keywords, and optional JD terms."""
    role_tokens = _tokenize_role(target_role)
    bank = _role_bank_keywords(target_role)
    jd = _jd_keywords(job_description or "")

    combined: List[str] = []
    for term in role_tokens + bank + jd:
        t = term.strip().lower()
        if not t or t in _STOPWORDS:
            continue
        if t not in combined:
            combined.append(t)

    if not combined:
        combined = ["software", "developer", "engineering"]
    return combined[:18]


def _keyword_analysis(
    resume_lower: str,
    target_role: str,
    job_description: Optional[str] = None,
) -> Tuple[int, List[str], List[str]]:
    primary = _build_keyword_targets(target_role, job_description)

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


def _is_likely_resume(text: str) -> tuple[bool, str]:
    """
    Lightweight resume classifier to block arbitrary PDFs from being scored as resumes.
    Deterministic and fast: requires multiple resume-structure signals.
    """
    t = (text or "").strip()
    if len(t) < 200:
        return False, "The uploaded file does not look like a resume (too little structured content)."

    lower = t.lower()

    has_email = re.search(r"[a-z0-9._%+-]+@[a-z0-9.-]+\.[a-z]{2,}", t, re.I) is not None
    has_phone = re.search(r"(\+?\d[\d\s\-\(\)]{7,}\d)", t) is not None
    section_hits = sum(1 for p in _SECTION_PATTERNS if re.search(p, lower))
    has_skillish = re.search(
        r"\b(skills?|technologies|tech stack|programming|languages?|frameworks?|tools?)\b",
        lower,
    ) is not None
    has_timeline = re.search(
        r"\b(19|20)\d{2}\b|\b(present|current)\b|\b(intern(ship)?|engineer|developer|analyst)\b",
        lower,
    ) is not None
    bulletish = sum(
        1
        for ln in t.splitlines()
        if re.match(r"^\s*[\-\u2022\u2023\*]\s+", ln) or re.match(r"^\s*\d+[\.)]\s+", ln)
    )

    score = 0
    score += 2 if has_email else 0
    score += 2 if has_phone else 0
    score += min(4, section_hits)  # up to 4 points
    score += 1 if has_skillish else 0
    score += 1 if has_timeline else 0
    score += 1 if bulletish >= 2 else 0

    # Require evidence from multiple independent resume signals.
    # Typical resumes pass comfortably; random docs rarely satisfy this.
    if score >= 6 and section_hits >= 2 and (has_email or has_phone):
        return True, ""
    return (
        False,
        "The uploaded file appears to be non-resume content. Please upload a resume/CV with sections like Experience, Education, and Skills.",
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


def _score_label(score: int) -> str:
    if score >= 80:
        return "Strong"
    if score >= 60:
        return "Moderate"
    return "Low"


def _visibility_band(score: int) -> str:
    if score >= 80:
        return "80+ — strong visibility; align Naukri headline and key skills with this resume."
    if score >= 60:
        return "60–79 — moderate; many recruiters filter below 70 on Naukri — prioritize checklist fixes."
    return "Below 60 — low recruiter search visibility; fix killers and keywords first."


def _count_skills(text: str) -> int:
    lower = text.lower()
    m = re.search(
        r"(?:^|\n)\s*(?:skills?|technical skills?|key skills?|technologies|tech stack)\s*[:\-]?\s*\n?([\s\S]{0,2500})",
        lower,
        re.I,
    )
    if not m:
        return 0
    block = m.group(1)
    # Stop at next major section heading
    block = re.split(
        r"\n\s*(?:experience|education|projects?|certifications?|achievements?|summary)\b",
        block,
        maxsplit=1,
        flags=re.I,
    )[0]
    items: Set[str] = set()
    for ln in block.splitlines():
        ln = ln.strip().lstrip("-•*·").strip()
        if not ln or len(ln) < 2:
            continue
        if "," in ln:
            for part in ln.split(","):
                p = part.strip()
                if 2 <= len(p) <= 40:
                    items.add(p.lower())
        elif 2 <= len(ln) <= 40:
            items.add(ln.lower())
    return len(items)


def _has_summary_section(text: str) -> bool:
    lower = text.lower()
    return bool(
        re.search(r"\b(summary|professional summary|career summary|objective|profile)\b", lower)
        or re.search(r"\babout me\b", lower)
    )


def _headline_matches_role(text: str, target_role: str) -> bool:
    head = "\n".join(text.splitlines()[:4]).lower()
    tr = (target_role or "").lower()
    tokens = [t for t in _tokenize_role(tr) if len(t) >= 3]
    if not tokens:
        return False
    hits = sum(1 for t in tokens if _word_boundary_match(head, t))
    return hits >= max(1, len(tokens) // 2)


def _section_scores(text: str, target_role: str) -> dict[str, int]:
    lower = text.lower()
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]

    contact = 0
    if re.search(r"[a-z0-9._%+-]+@[a-z0-9.-]+\.[a-z]{2,}", text, re.I):
        contact += 45
    if re.search(r"(\+?\d[\d\s\-\(\)]{7,}\d)", text):
        contact += 35
    if re.search(r"\b(linkedin|github)\b", lower):
        contact += 20

    headline = 25
    if lines and len(lines[0]) <= 90:
        headline += 20
    if _headline_matches_role(text, target_role):
        headline += 35
    elif re.search(r"\b(engineer|developer|analyst|intern|manager|designer)\b", lower[:500]):
        headline += 15

    summary = 20
    if _has_summary_section(text):
        summary += 45
    summary_lines = [
        ln
        for ln in lines[:25]
        if 40 <= len(ln) <= 220 and not re.search(r"@|linkedin|github|phone|\d{10}", ln, re.I)
    ]
    if summary_lines:
        summary += min(35, len(summary_lines) * 12)

    skills_n = _count_skills(text)
    if skills_n >= 12:
        skills = 95
    elif skills_n >= 10:
        skills = 85
    elif skills_n >= 6:
        skills = 65
    elif skills_n >= 3:
        skills = 45
    else:
        skills = 25

    experience = 20
    if re.search(r"\b(experience|work history|employment)\b", lower):
        experience += 30
    bullets = sum(
        1
        for ln in lines
        if re.match(r"^[\-\u2022\u2023\*]\s+", ln) or re.match(r"^\d+[\.)]\s+", ln)
    )
    experience += min(35, bullets * 4)
    if re.search(r"\b(19|20)\d{2}\b", lower) and re.search(r"\b(present|current)\b", lower):
        experience += 15

    education = 20
    if re.search(r"\beducation\b", lower):
        education += 45
    if re.search(r"\b(b\.?tech|b\.?e\.?|m\.?tech|bachelor|master|degree|university|college|cgpa|gpa)\b", lower):
        education += 35

    return {
        "headline": max(0, min(100, headline)),
        "summary": max(0, min(100, summary)),
        "experience": max(0, min(100, experience)),
        "skills": max(0, min(100, skills)),
        "education": max(0, min(100, education)),
        "contact": max(0, min(100, contact)),
    }


def _format_warnings(text: str) -> List[dict[str, str]]:
    warnings: List[dict[str, str]] = []
    letters = sum(1 for c in text if c.isalpha())
    ratio = letters / max(len(text), 1)
    if len(text) > 50 and ratio < 0.35:
        warnings.append(
            {
                "code": "image_heavy",
                "message": "Very little extractable text — image-only or scanned PDFs hurt Naukri parsing.",
                "severity": "fail",
            }
        )
    if len(text) > 14_000:
        warnings.append(
            {
                "code": "too_long",
                "message": "Resume is very long; Naukri recommends 2–3 pages with a concise summary.",
                "severity": "warn",
            }
        )
    if len(text) < 400:
        warnings.append(
            {
                "code": "too_short",
                "message": "Resume content is thin — add projects, skills, and experience bullets.",
                "severity": "warn",
            }
        )
    section_hits = sum(1 for p in _SECTION_PATTERNS if re.search(p, text.lower()))
    if section_hits < 3:
        warnings.append(
            {
                "code": "missing_sections",
                "message": "Add clear sections: Experience, Education, Skills (and Projects for freshers).",
                "severity": "fail",
            }
        )
    skills_n = _count_skills(text)
    if skills_n < 6:
        warnings.append(
            {
                "code": "few_skills",
                "message": f"Only ~{skills_n} skills detected; Naukri ranks better with 10–15 key skills.",
                "severity": "warn",
            }
        )
    return warnings


def _naukri_checklist(text: str, target_role: str, impact: int) -> List[dict[str, Any]]:
    skills_n = _count_skills(text)
    has_summary = _has_summary_section(text)
    headline_ok = _headline_matches_role(text, target_role)
    has_contact = bool(re.search(r"[a-z0-9._%+-]+@[a-z0-9.-]+\.[a-z]{2,}", text, re.I))
    has_exp = bool(re.search(r"\b(experience|projects?)\b", text.lower()))
    has_edu = bool(re.search(r"\beducation\b", text.lower()))
    has_metrics = impact >= 65

    def _status(passed: bool, partial: bool = False) -> str:
        if passed:
            return "pass"
        if partial:
            return "warn"
        return "fail"

    return [
        {
            "item": "10–15 key skills listed",
            "status": _status(skills_n >= 10, skills_n >= 6),
            "detail": "Mirror these on Naukri Key Skills for recruiter search.",
            "current": skills_n,
            "target": 15,
        },
        {
            "item": "Professional summary or objective",
            "status": _status(has_summary),
            "detail": "3–5 lines with role title and top skills.",
        },
        {
            "item": "Headline matches target role",
            "status": _status(headline_ok),
            "detail": f"Align with “{target_role}” in the first lines and Naukri headline.",
        },
        {
            "item": "Contact information present",
            "status": _status(has_contact),
            "detail": "Email and phone should be easy to find.",
        },
        {
            "item": "Experience or projects with bullets",
            "status": _status(has_exp),
            "detail": "Freshers: prioritize 2 strong projects with tech stack.",
        },
        {
            "item": "Education section complete",
            "status": _status(has_edu),
            "detail": "Degree, institution, and graduation year.",
        },
        {
            "item": "Quantified achievements",
            "status": _status(has_metrics, impact >= 50),
            "detail": "Add %, scale, users, or team size where truthful.",
        },
        {
            "item": "ATS-friendly text format",
            "status": _status(not any(w["severity"] == "fail" for w in _format_warnings(text))),
            "detail": "Single-column PDF/DOCX; avoid image-only layouts.",
        },
    ]


def _naukri_readiness(overall: int, section_scores: dict[str, int]) -> dict[str, Any]:
    weights = {
        "skills": 0.30,
        "headline": 0.20,
        "summary": 0.15,
        "experience": 0.20,
        "contact": 0.10,
        "education": 0.05,
    }
    profile_alignment = int(
        round(sum(section_scores.get(k, 0) * w for k, w in weights.items()))
    )
    label = _score_label(profile_alignment)
    return {
        "resume_document": overall,
        "profile_alignment": profile_alignment,
        "label": label,
        "visibility_band": _visibility_band(profile_alignment),
    }


def _overall_weighted(
    keyword: int,
    formatting: int,
    impact: int,
    ats: int,
    candidate_type: Optional[str] = None,
) -> int:
    ct = (candidate_type or "").lower().replace(" ", "_")
    if ct in ("college_student", "fresher", "student"):
        return int(round(0.30 * keyword + 0.25 * formatting + 0.20 * impact + 0.25 * ats))
    return int(round(0.35 * keyword + 0.20 * formatting + 0.25 * impact + 0.20 * ats))


def _infer_candidate_type(experience_years: Optional[int], text: str) -> Optional[str]:
    if experience_years is not None:
        return "college_student" if experience_years <= 1 else "experienced"
    lower = text.lower()
    if re.search(r"\b(intern(ship)?|fresher|student|b\.?tech|college|university)\b", lower):
        return "college_student"
    if re.search(r"\b\d+\+?\s*(years?|yrs?)\s+(of\s+)?experience\b", lower):
        return "experienced"
    return None


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


def analyze_resume(
    text: str,
    target_role: str,
    *,
    candidate_type: Optional[str] = None,
    experience_years: Optional[int] = None,
    job_description: Optional[str] = None,
) -> dict:
    ok_resume, reason = _is_likely_resume(text)
    if not ok_resume:
        raise ValueError(reason)

    tr = (target_role or "").strip() or "Software Developer"
    resume_lower = text.lower()

    resolved_type = (candidate_type or "").strip() or _infer_candidate_type(experience_years, text)
    kw_score, matched, missing = _keyword_analysis(resume_lower, tr, job_description)
    fmt = _formatting_score(text)
    imp = _impact_score(text)
    ats = _ats_parse_score(text)
    overall = _overall_weighted(kw_score, fmt, imp, ats, resolved_type)
    sections = _section_scores(text, tr)
    fmt_warnings = _format_warnings(text)
    checklist = _naukri_checklist(text, tr, imp)
    naukri = _naukri_readiness(overall, sections)
    skills_n = _count_skills(text)

    payload: dict[str, Any] = {
        "score": overall,
        "score_label": _score_label(overall),
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
        "section_scores": sections,
        "naukri_checklist": checklist,
        "naukri_readiness": naukri,
        "format_warnings": fmt_warnings,
        "skills_count": skills_n,
    }
    if resolved_type:
        payload["candidate_type"] = resolved_type
    if experience_years is not None:
        payload["experience_years"] = experience_years
    if (job_description or "").strip():
        payload["job_description_provided"] = True
    return payload


def _parse_llm_coaching_json(content: str) -> Optional[dict[str, Any]]:
    """Extract first JSON object from model output (strip ```json fences when present)."""
    content = (content or "").strip()
    if not content:
        return None
    stripped = re.sub(r"^```(?:json)?\s*", "", content, flags=re.IGNORECASE | re.MULTILINE)
    stripped = re.sub(r"\s*```\s*$", "", stripped, flags=re.MULTILINE).strip()
    for candidate in (stripped, content):
        try:
            obj = json.loads(candidate)
            if isinstance(obj, dict):
                return obj
        except json.JSONDecodeError:
            pass
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


def _sanitize_resume_ats_llm_output(obj: dict[str, Any]) -> Optional[dict[str, Any]]:
    """Map LLM JSON to merge keys for ResumeAtsResponse (does not touch heuristic scores)."""
    if not isinstance(obj, dict):
        return None
    if obj.get("error"):
        return None

    out: dict[str, Any] = {}

    s = obj.get("summary")
    if isinstance(s, str) and s.strip():
        out["summary"] = s.strip()[:4000]

    ct = obj.get("candidate_type")
    if isinstance(ct, str) and ct.strip():
        out["candidate_type"] = ct.strip()[:120]

    ir = obj.get("inferred_role")
    if isinstance(ir, str) and ir.strip():
        out["inferred_role"] = ir.strip()[:300]

    def _str_list(key: str, max_n: int, max_len: int) -> None:
        raw = obj.get(key)
        if not isinstance(raw, list):
            return
        clean: List[str] = []
        for x in raw[:max_n]:
            if isinstance(x, str) and x.strip():
                clean.append(x.strip()[:max_len])
        if clean:
            out[key] = clean

    _str_list("top_resume_killers", 5, 600)
    _str_list("strengths", 8, 800)
    _str_list("fixes", 12, 800)
    _str_list("keyword_gaps", 12, 600)
    _str_list("rewrite_examples", 8, 1200)
    _str_list("positioning_improvement", 10, 800)
    _str_list("portal_tips", 12, 800)
    _str_list("priority_action_plan", 8, 600)

    sr = obj.get("section_rewrites")
    if isinstance(sr, dict):
        section: dict[str, Any] = {}
        for k, maxlen in (("headline", 800), ("summary", 2500), ("skills", 2500)):
            v = sr.get(k)
            if isinstance(v, str) and v.strip():
                section[k] = v.strip()[:maxlen]
        pe = sr.get("project_or_experience")
        if isinstance(pe, list):
            bullets = []
            for x in pe[:8]:
                if isinstance(x, str) and x.strip():
                    bullets.append(x.strip()[:1200])
            if bullets:
                section["project_or_experience"] = bullets
        if section:
            out["section_rewrites"] = section

    sb = obj.get("score_breakdown")
    if isinstance(sb, dict):
        sb_out: dict[str, str] = {}
        for k, maxlen in (
            ("keyword_match", 24),
            ("impact", 24),
            ("structure", 24),
            ("ats_readability", 24),
        ):
            v = sb.get(k)
            if isinstance(v, str) and v.strip():
                sb_out[k] = v.strip()[:maxlen]
        if sb_out:
            out["score_breakdown"] = sb_out

    est = obj.get("ats_score_estimate")
    if isinstance(est, dict):
        score_s = est.get("score")
        reason_s = est.get("reason")
        label_s = est.get("label")
        est_out: dict[str, str] = {}
        if isinstance(score_s, str) and score_s.strip():
            est_out["score"] = score_s.strip()[:40]
        if isinstance(label_s, str) and label_s.strip():
            est_out["label"] = label_s.strip()[:200]
        if isinstance(reason_s, str) and reason_s.strip():
            est_out["reason"] = reason_s.strip()[:2000]
        if est_out:
            out["ats_score_estimate"] = est_out

    if out:
        return out
    return None


async def enrich_analysis_with_llm(
    payload: dict,
    resume_text: str,
    target_role: str,
    job_description: Optional[str] = None,
) -> dict:
    """
    Enrich resume ATS response via OpenAI (transformation / coaching JSON).
    Numeric scores and matched/missing keywords stay from heuristics.
    On any failure or LLM error-only response, returns payload unchanged.
    """
    from app.core.config import settings

    if not settings.resume_ats_use_llm:
        return payload

    excerpt = resume_text[:RESUME_LLM_MAX_INPUT_CHARS]
    if len(resume_text) > RESUME_LLM_MAX_INPUT_CHARS:
        excerpt += "\n\n[… resume truncated for analysis …]"

    timeout_sec = min(90, max(25, int(settings.llm_timeout_seconds)))

    tr = (target_role or "").strip() or "Software Developer"
    matched = payload.get("matched_keywords") or []
    missing = payload.get("missing_keywords") or []
    snapshot = (
        f"Target role (form): {tr}\n"
        f"Overall score (heuristic): {payload.get('score')}/100 ({payload.get('score_label')})\n"
        f"Breakdown — keywords: {payload.get('keywords')}, formatting: {payload.get('formatting')}, "
        f"impact: {payload.get('impact')}, ATS parse: {payload.get('ats')}\n"
        f"Skills detected: {payload.get('skills_count')}\n"
        f"Matched role keywords: {', '.join(matched) or '(none)'}\n"
        f"Missing role keywords: {', '.join(missing) or '(none)'}\n"
        f"Naukri profile alignment (heuristic): {payload.get('naukri_readiness', {}).get('profile_alignment')}\n"
    )

    experience_years = str(payload.get("experience_years") or "not provided — infer from resume")
    candidate_type_hint = str(
        payload.get("candidate_type") or "not provided — infer college_student vs experienced from resume"
    )
    jd_excerpt = (job_description or "").strip()[:4000] or "not provided"

    prompt = render_resume_ats_enrich_prompt(
        candidate_type=candidate_type_hint,
        experience_years=experience_years,
        target_role=tr,
        snapshot=snapshot,
        excerpt=excerpt,
        job_description=jd_excerpt,
    )

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

    if parsed.get("error"):
        logger.warning("Resume ATS LLM returned error object; keeping heuristic payload")
        return payload

    coaching = _sanitize_resume_ats_llm_output(parsed)
    if not coaching:
        return payload

    return {**payload, **coaching}

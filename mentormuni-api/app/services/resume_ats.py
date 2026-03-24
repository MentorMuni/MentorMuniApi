import io
import logging
import re
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import List, Optional, Set, Tuple

from pypdf import PdfReader

logger = logging.getLogger("resume_ats")

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
    }

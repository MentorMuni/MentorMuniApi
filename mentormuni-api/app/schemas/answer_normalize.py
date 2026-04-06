"""Normalize user-submitted answers for interview evaluate endpoint."""

from typing import Final

_CANONICAL: Final[frozenset[str]] = frozenset({"Yes", "No", "A", "B", "C", "D"})


def normalize_interview_answer(raw) -> str:
    """
    Canonical form: Yes | No | A | B | C | D
    Accepts common variants: y/n, a-d (case-insensitive).
    """
    if raw is None:
        raise ValueError("answer cannot be empty")
    s = str(raw).strip()
    if not s:
        raise ValueError("answer cannot be empty")
    low = s.lower()
    if low in ("yes", "y"):
        return "Yes"
    if low in ("no", "n"):
        return "No"
    c0 = s[0].upper()
    if c0 in "ABCD" and len(s) == 1:
        return c0
    if len(s) >= 2 and c0 in "ABCD" and s[1] in ").:":
        return c0
    raise ValueError(
        f"answer must be Yes, No, or A–D (multiple choice), got: {raw!r}"
    )


def is_valid_canonical_answer(s: str) -> bool:
    return s in _CANONICAL

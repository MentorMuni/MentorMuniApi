"""
Validation for primary_skill (tech stack) - block inappropriate input only.
Accepts any technical skill; no allowlist (100+ skills exist).
"""
import re

# Blocked terms (word boundary to avoid blocking "class", "pass", "regex")
BLOCKED_PATTERNS = [
    r"\bporn\b", r"\bxxx\b", r"\bsex\b", r"\bnude\b", r"\bnaked\b", r"\badult\b", r"\bnsfw\b",
    r"\bhack\b", r"\bcrack\b", r"\bpirate\b", r"\billegal\b",
    r"\bspam\b", r"\bscam\b", r"\bphish\b", r"\bmalware\b", r"\bvirus\b",
    r"\basdf\b", r"\bqwerty\b", r"testing123", r"xyz123", r"^sample$",
    r"\bfuck", r"\bshit\b", r"\bdick\b", r"\bbitch\b", r"\bretard\b",
]

# Comma allowed for multi-topic strings (e.g. "DSA, OOP, DBMS") on interview readiness
VALID_PATTERN = re.compile(r"^[a-zA-Z0-9\.\-\s\/#\+,]+$")


def validate_primary_skill(value: str) -> str:
    """
    Validate primary_skill - block inappropriate content only.
    Accepts any tech stack; no allowlist.
    """
    if not value or not isinstance(value, str):
        raise ValueError("Primary skill is required")

    v = value.strip()
    if len(v) < 2:
        raise ValueError("Please enter a valid technical skill (e.g. React, .NET, Python)")

    v_lower = v.lower()

    # Block inappropriate content
    for pat in BLOCKED_PATTERNS:
        if re.search(pat, v_lower):
            raise ValueError(
                "Please enter a valid technical skill such as React, .NET, Java, or Python"
            )

    # Pattern: letters, numbers, dots, hyphens, spaces
    if not VALID_PATTERN.match(v):
        raise ValueError(
            "Please enter a valid technical skill using letters and numbers "
            "(e.g. React, .NET, Java, Python)"
        )

    return v

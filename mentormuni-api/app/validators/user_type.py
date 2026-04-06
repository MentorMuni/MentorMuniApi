"""Shared user_type normalization: college years + it_professional, with legacy aliases."""

from typing import Final

ALLOWED_USER_TYPES: Final[frozenset[str]] = frozenset(
    {
        "college_student_year_1",
        "college_student_year_2",
        "college_student_year_3",
        "college_student_year_4",
        "recent_graduate",
        "it_professional",
    }
)

_SHORT_ALIASES: Final[dict[str, str]] = {
    "year_1": "college_student_year_1",
    "year_2": "college_student_year_2",
    "year_3": "college_student_year_3",
    "year_4": "college_student_year_4",
    "y1": "college_student_year_1",
    "y2": "college_student_year_2",
    "y3": "college_student_year_3",
    "y4": "college_student_year_4",
}

# Backward-compatible mappings from older API / UI strings
_LEGACY_ALIASES: Final[dict[str, str]] = {
    "student": "college_student_year_4",
    "1st_year_student": "college_student_year_1",
    "2nd_year_student": "college_student_year_2",
    "3rd_year_student": "college_student_year_3",
    "4th_year_student": "college_student_year_4",
    "final_year_student": "college_student_year_4",
    "recent_graduate": "recent_graduate",
    "recentgraduate": "recent_graduate",
    "working_professional": "it_professional",
    "workingprofessional": "it_professional",
}


def normalize_user_type(v: str) -> str:
    """
    Canonical values: college_student_year_1..4, it_professional.

    Accepts short aliases (y3, year_3), legacy "student"/"working professional",
    and 3rd/4th year phrasing.
    """
    key = v.lower().strip().replace(" ", "_").replace("-", "_")
    if key in _SHORT_ALIASES:
        key = _SHORT_ALIASES[key]
    if key == "itprofessional":
        key = "it_professional"
    if key in _LEGACY_ALIASES:
        key = _LEGACY_ALIASES[key]
    if key not in ALLOWED_USER_TYPES:
        raise ValueError(
            "user_type must be one of: college_student_year_1, college_student_year_2, "
            "college_student_year_3, college_student_year_4, recent_graduate, it_professional "
            "(legacy: student, 3rd/4th year student, recent graduate, working professional)"
        )
    return key


def infer_interview_user_category(canonical_user_type: str) -> str:
    """
    Frontend placement buckets: 3rd_year (1st–3rd), 4th_year, recent_graduate, working_professional.
    """
    if canonical_user_type == "it_professional":
        return "working_professional"
    if canonical_user_type == "recent_graduate":
        return "recent_graduate"
    if canonical_user_type == "college_student_year_4":
        return "4th_year"
    if canonical_user_type in (
        "college_student_year_1",
        "college_student_year_2",
        "college_student_year_3",
    ):
        return "3rd_year"
    return "3rd_year"

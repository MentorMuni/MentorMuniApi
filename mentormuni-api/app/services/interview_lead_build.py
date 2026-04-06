"""Build Interview Ready lead dicts for JSONL (server-side plan flows)."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional

from app.schemas.ai import InterviewReadinessPlanRequest
from app.validators.user_type import infer_interview_user_category

# Canonical API user_type -> display string for lead storage (frontend examples)
_DISPLAY_USER_TYPE: dict[str, str] = {
    "college_student_year_1": "1st Year Student",
    "college_student_year_2": "2nd Year Student",
    "college_student_year_3": "3rd Year Student",
    "college_student_year_4": "4th Year Student",
    "recent_graduate": "Recent Graduate",
    "it_professional": "working professional",
}


def display_user_type(canonical: str) -> str:
    return _DISPLAY_USER_TYPE.get(canonical, canonical)


def storage_user_category(canonical_user_type: str) -> str:
    """Maps inferred category to frontend lead value (professional not working_professional)."""
    x = infer_interview_user_category(canonical_user_type)
    if x == "working_professional":
        return "professional"
    return x


def iso_timestamp_utc() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def lead_from_legacy_plan(
    *,
    email: Optional[str],
    phone: Optional[str],
    user_type_canonical: str,
    primary_skill: str,
    target_role: Optional[str],
    experience_years: int = 0,
    assessment_focus: Optional[str] = "placement",
) -> Optional[dict[str, Any]]:
    if not (email and str(email).strip()) and not (phone and str(phone).strip()):
        return None
    return {
        "email": (email or "").strip() or None,
        "phone": (phone or "").strip() or None,
        "user_type": display_user_type(user_type_canonical),
        "user_category": storage_user_category(user_type_canonical),
        "primary_skill": primary_skill,
        "college_name": None,
        "company_name": None,
        "current_organization": None,
        "experience_years": experience_years,
        "assessment_focus": assessment_focus,
        "target_role": target_role,
        "skill_readiness_user_type": None,
        "source": "interview_ready_generate_questions",
        "captured_at": iso_timestamp_utc(),
    }


def lead_from_skill_readiness(
    *,
    email: Optional[str],
    phone: Optional[str],
    user_type_canonical: str,
    primary_skill: str,
    target_role: Optional[str],
    experience_years: int = 0,
    assessment_focus: str = "skill",
) -> Optional[dict[str, Any]]:
    if not (email and str(email).strip()) and not (phone and str(phone).strip()):
        return None
    return {
        "email": (email or "").strip() or None,
        "phone": (phone or "").strip() or None,
        "user_type": display_user_type(user_type_canonical),
        "user_category": storage_user_category(user_type_canonical),
        "primary_skill": primary_skill,
        "college_name": None,
        "company_name": None,
        "current_organization": None,
        "experience_years": experience_years,
        "assessment_focus": assessment_focus,
        "target_role": target_role,
        "skill_readiness_user_type": user_type_canonical,
        "source": "interview_ready_generate_questions",
        "captured_at": iso_timestamp_utc(),
    }


def lead_from_interview_readiness(body: InterviewReadinessPlanRequest) -> Optional[dict[str, Any]]:
    """InterviewReadinessPlanRequest — full placement/pro context."""
    email, phone = body.email, body.phone
    if not (email and str(email).strip()) and not (phone and str(phone).strip()):
        return None

    ut = body.user_type
    cat = body.user_category or infer_interview_user_category(ut)
    uc_store = "professional" if cat == "working_professional" else cat

    d: dict[str, Any] = {
        "email": (email or "").strip() or None,
        "phone": (phone or "").strip() or None,
        "user_type": display_user_type(ut),
        "user_category": uc_store,
        "primary_skill": body.primary_skill,
        "college_name": body.college_name,
        "company_name": body.current_organization,
        "current_organization": body.current_organization,
        "experience_years": body.experience_years or 0,
        "assessment_focus": body.assessment_focus,
        "target_role": body.target_role,
        "skill_readiness_user_type": None,
        "source": "interview_ready_generate_questions",
        "captured_at": iso_timestamp_utc(),
    }
    placement = body.assessment_focus == "placement"
    if placement and cat in ("4th_year", "recent_graduate"):
        d["campus_or_off_campus"] = body.campus_or_off_campus
        d["targets_service_mnc"] = body.targets_service_mnc
        d["targets_product_company"] = body.targets_product_company
        d["target_companies_notes"] = body.target_companies_notes
        d["specific_role_requested"] = body.specific_role_requested
        d["specific_role"] = body.specific_role
    if placement and (cat == "working_professional" or ut == "it_professional"):
        d["core_skill"] = body.core_skill
        d["jd_provided"] = body.jd_provided
        d["job_description"] = body.job_description
        d["target_company_name"] = body.target_company_name
    return d

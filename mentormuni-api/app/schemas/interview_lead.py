"""Payload for Interview Ready lead capture (POST /admin/leads and server-side plan flows)."""

from datetime import datetime, timezone
from typing import Any, Optional

from pydantic import BaseModel, Field, field_validator, model_validator


class InterviewReadyLeadCreate(BaseModel):
    """
    Mirrors the frontend lead shape for interview-ready question generation.
    At least one of email or phone should be present for a useful lead.
    """

    email: Optional[str] = None
    phone: Optional[str] = None
    user_type: str = Field(..., min_length=1, description='Display or API label, e.g. "4th Year Student"')
    user_category: Optional[str] = Field(
        default=None,
        description="3rd_year | 4th_year | recent_graduate | professional",
    )
    primary_skill: str = Field(..., min_length=1)
    college_name: Optional[str] = None
    company_name: Optional[str] = None
    current_organization: Optional[str] = None
    experience_years: int = Field(default=0, ge=0, le=50)
    assessment_focus: Optional[str] = Field(
        default=None,
        description='e.g. "skill" | "placement"',
    )
    target_role: Optional[str] = None
    skill_readiness_user_type: Optional[str] = Field(
        default=None,
        description="Canonical skill flow only, e.g. college_student_year_4",
    )
    source: str = Field(default="interview_ready_generate_questions")
    captured_at: Optional[str] = Field(
        default=None,
        description="ISO-8601; set server-side if omitted",
    )
    campus_or_off_campus: Optional[str] = None
    targets_service_mnc: Optional[bool] = None
    targets_product_company: Optional[bool] = None
    target_companies_notes: Optional[str] = None
    specific_role_requested: Optional[bool] = None
    specific_role: Optional[str] = None
    core_skill: Optional[str] = None
    jd_provided: Optional[bool] = None
    job_description: Optional[str] = None
    target_company_name: Optional[str] = None

    @field_validator("email", "phone", "college_name", "company_name", "current_organization", "target_role", "target_companies_notes", "specific_role", "core_skill", "job_description", "target_company_name", "campus_or_off_campus")
    @classmethod
    def empty_str_to_none(cls, v: Any):
        if v is None:
            return None
        if isinstance(v, str) and not v.strip():
            return None
        return v

    @model_validator(mode="after")
    def set_captured_at(self):
        if not self.captured_at or not str(self.captured_at).strip():
            object.__setattr__(
                self,
                "captured_at",
                datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            )
        return self

    @model_validator(mode="after")
    def require_contact(self):
        if not (self.email and str(self.email).strip()) and not (self.phone and str(self.phone).strip()):
            raise ValueError("At least one of email or phone is required")
        return self

    def to_storage_dict(self) -> dict:
        """JSON-serializable dict for JSONL (None for empty optional strings)."""
        d = self.model_dump(mode="json", exclude_none=False)
        # Normalize empties to null for string fields
        for k, v in list(d.items()):
            if isinstance(v, str) and not v.strip():
                d[k] = None
        return d

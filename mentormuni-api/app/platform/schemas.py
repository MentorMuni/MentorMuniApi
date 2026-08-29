"""Pydantic schemas for Platform Admin portal."""

from __future__ import annotations

from datetime import date, datetime
from typing import Any, Optional

from pydantic import BaseModel, EmailStr, Field, field_validator


# ----- Auth -----


class PlatformLoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1)


class PlatformTokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in_minutes: int


class PlatformMeResponse(BaseModel):
    id: int
    name: str
    email: str
    role: str
    status: str
    must_change_password: bool = False
    created_at: datetime

    model_config = {"from_attributes": True}


class PlatformChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str = Field(min_length=8, max_length=128)


# ----- Activate TPO (org portal user via platform invite) -----


class ActivateTpoResponse(BaseModel):
    message: str
    organization_code: Optional[str] = None


class MessageResponse(BaseModel):
    message: str


# ----- Organizations -----


class PlatformOrganizationCreate(BaseModel):
    name: str = Field(min_length=2, max_length=255)
    code: str = Field(min_length=2, max_length=64)
    # College short name → medicaps.mentormuni.com (optional; derived from code if omitted)
    portal_slug: Optional[str] = Field(default=None, max_length=64)
    organization_type: str = Field(pattern="^(COLLEGE|PUBLIC)$")
    status: str = Field(default="ACTIVE", pattern="^(ACTIVE|SUSPENDED)$")
    contact_person: Optional[str] = None
    contact_email: Optional[EmailStr] = None
    contact_phone: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    country: Optional[str] = "India"


class PlatformOrganizationUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=2, max_length=255)
    code: Optional[str] = Field(default=None, min_length=2, max_length=64)
    portal_slug: Optional[str] = Field(default=None, max_length=64)
    organization_type: Optional[str] = Field(
        default=None, pattern="^(COLLEGE|PUBLIC)$"
    )
    status: Optional[str] = Field(default=None, pattern="^(ACTIVE|SUSPENDED)$")
    contact_person: Optional[str] = None
    contact_email: Optional[EmailStr] = None
    contact_phone: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    country: Optional[str] = None


class PlatformOrganizationResponse(BaseModel):
    id: int
    name: str
    code: str
    portal_slug: Optional[str] = None
    portal_url: Optional[str] = None
    organization_type: str
    status: str
    contact_person: Optional[str] = None
    contact_email: Optional[str] = None
    contact_phone: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    country: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class PlatformOrganizationListResponse(BaseModel):
    items: list[PlatformOrganizationResponse]
    total: int


# ----- Subscriptions -----


class PlatformSubscriptionCreate(BaseModel):
    organization_id: int
    plan_id: int
    student_limit: Optional[int] = Field(default=None, ge=1)
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    status: str = Field(default="ACTIVE", pattern="^(ACTIVE|EXPIRED|CANCELLED)$")


class PlatformSubscriptionUpdate(BaseModel):
    plan_id: Optional[int] = None
    student_limit: Optional[int] = Field(default=None, ge=1)
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    status: Optional[str] = Field(default=None, pattern="^(ACTIVE|EXPIRED|CANCELLED)$")


class PlatformSubscriptionResponse(BaseModel):
    id: int
    organization_id: int
    organization_code: Optional[str] = None
    organization_name: Optional[str] = None
    plan_id: int
    plan_name: str
    student_limit: int
    used_students: int
    start_date: date
    end_date: date
    status: str
    created_at: datetime


class PlatformSubscriptionListResponse(BaseModel):
    items: list[PlatformSubscriptionResponse]
    total: int


# ----- Features -----


class FeatureCatalogResponse(BaseModel):
    id: int
    feature_code: str
    feature_name: str
    category: Optional[str] = None
    description: Optional[str] = None
    status: str

    model_config = {"from_attributes": True}


class OrgFeatureItem(BaseModel):
    feature_id: int
    feature_code: str
    feature_name: str
    enabled: bool
    configuration_json: Optional[dict[str, Any]] = None


class OrgFeaturesResponse(BaseModel):
    organization_id: int
    features: list[OrgFeatureItem]


class OrgFeatureToggle(BaseModel):
    feature_id: int
    enabled: bool
    configuration_json: Optional[dict[str, Any]] = None


class OrgFeaturesSaveRequest(BaseModel):
    features: list[OrgFeatureToggle]


# ----- TPO / Org Admin (ORG_ADMIN with title TPO|DEAN|DIRECTOR) -----

ORG_ADMIN_TITLES = ("TPO", "DEAN", "DIRECTOR")


class CreateTpoRequest(BaseModel):
    first_name: str = Field(min_length=1, max_length=128)
    last_name: str = Field(min_length=1, max_length=128)
    email: EmailStr
    mobile: Optional[str] = None
    username: str = Field(min_length=3, max_length=128)
    # TPO (primary) | DEAN | DIRECTOR — same ORG_ADMIN access
    title: str = Field(default="TPO", description="TPO | DEAN | DIRECTOR")
    # Optional override; default = 72 hours
    activation_hours: int = Field(default=72, ge=1, le=168)

    @field_validator("title")
    @classmethod
    def normalize_title(cls, value: str) -> str:
        code = str(value or "TPO").strip().upper()
        if code not in ORG_ADMIN_TITLES:
            raise ValueError(f"title must be one of: {', '.join(ORG_ADMIN_TITLES)}")
        return code


class UpdateTpoRequest(BaseModel):
    """
    Change Org Admin details on an existing ORG_ADMIN row (same user id).

    Pass user_id when the org has multiple admins (TPO / Dean / Director).
    """

    user_id: Optional[int] = Field(
        default=None,
        description="Required when org has more than one Org Admin.",
    )
    first_name: str = Field(min_length=1, max_length=128)
    last_name: str = Field(min_length=1, max_length=128)
    email: EmailStr
    mobile: Optional[str] = None
    username: str = Field(min_length=3, max_length=128)
    title: Optional[str] = Field(
        default=None,
        description="Optional retitle: TPO | DEAN | DIRECTOR",
    )
    activation_hours: int = Field(default=72, ge=1, le=168)
    # When true (default), clear password and send activate link to the new email.
    reset_password: bool = True

    @field_validator("title")
    @classmethod
    def normalize_optional_title(cls, value: Optional[str]) -> Optional[str]:
        if value is None or str(value).strip() == "":
            return None
        code = str(value).strip().upper()
        if code not in ORG_ADMIN_TITLES:
            raise ValueError(f"title must be one of: {', '.join(ORG_ADMIN_TITLES)}")
        return code


class CreateTpoResponse(BaseModel):
    id: int
    organization_id: int
    first_name: str
    last_name: str
    email: str
    username: str
    status: str
    title: str = "TPO"
    is_primary: bool = True
    display_role: str = "Org Admin"
    # Raw token returned once. Prefer email delivery; token still returned for ops fallback.
    activation_token: str
    # Full FE link (same URL embedded in the email). Path stays /activate-tpo.
    activation_url: str
    activation_expires_at: datetime
    message: str
    email_sent: bool = False
    email_skipped: bool = False
    email_detail: str = ""


class TpoListItem(BaseModel):
    id: int
    organization_id: int
    organization_code: Optional[str] = None
    organization_name: Optional[str] = None
    first_name: str
    last_name: str
    email: str
    username: str
    mobile: Optional[str] = None
    status: str
    title: str = "TPO"
    is_primary: bool = False
    display_role: str = "Org Admin"
    created_at: datetime
    activation_pending: bool


class TpoListResponse(BaseModel):
    items: list[TpoListItem]
    total: int


class DeactivateOrgAdminResponse(BaseModel):
    id: int
    organization_id: int
    title: str
    status: str
    message: str


class ActivateTpoRequest(BaseModel):
    token: str = Field(min_length=10)
    new_password: str = Field(min_length=8, max_length=128)


# ----- Individuals (PUBLIC students — MentorMuni staff only) -----


class CreateIndividualRequest(BaseModel):
    first_name: str = Field(min_length=1, max_length=128)
    last_name: str = Field(min_length=1, max_length=128)
    email: EmailStr
    mobile: Optional[str] = Field(default=None, max_length=32)
    username: Optional[str] = Field(default=None, min_length=2, max_length=128)
    # Personal / academic profile (not a college tenant).
    college_name: Optional[str] = Field(default=None, max_length=255)
    course_or_branch: Optional[str] = Field(default=None, max_length=128)
    batch_year: Optional[int] = Field(default=None, ge=1990, le=2100)
    roll_number: Optional[str] = Field(default=None, max_length=64)
    activation_hours: int = Field(default=72, ge=1, le=168)


class IndividualListItem(BaseModel):
    id: int
    first_name: str
    last_name: str
    email: str
    username: str
    mobile: Optional[str] = None
    status: str
    college_name: Optional[str] = None
    course_or_branch: Optional[str] = None
    batch_year: Optional[int] = None
    roll_number: Optional[str] = None
    created_at: datetime
    activation_pending: bool = False


class IndividualListResponse(BaseModel):
    items: list[IndividualListItem]
    total: int


class CreateIndividualResponse(BaseModel):
    id: int
    first_name: str
    last_name: str
    email: str
    username: str
    status: str
    college_name: Optional[str] = None
    course_or_branch: Optional[str] = None
    batch_year: Optional[int] = None
    roll_number: Optional[str] = None
    activation_token: str
    activation_url: str
    activation_expires_at: datetime
    message: str
    email_sent: bool = False
    email_skipped: bool = False
    email_detail: str = ""


# ----- Platform users -----


class PlatformUserCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    role: str = Field(pattern="^(PLATFORM_ADMIN|SUPPORT|SALES|OPERATIONS)$")


class PlatformUserUpdate(BaseModel):
    name: Optional[str] = None
    email: Optional[EmailStr] = None
    role: Optional[str] = Field(default=None, pattern="^(PLATFORM_ADMIN|SUPPORT|SALES|OPERATIONS)$")
    status: Optional[str] = Field(default=None, pattern="^(ACTIVE|INACTIVE)$")
    password: Optional[str] = Field(default=None, min_length=8, max_length=128)


class PlatformUserResponse(BaseModel):
    id: int
    name: str
    email: str
    role: str
    status: str
    must_change_password: bool = False
    created_at: datetime

    model_config = {"from_attributes": True}


# ----- Dashboard -----


class FeatureUsageItem(BaseModel):
    feature_code: str
    feature_name: str
    enabled_org_count: int


class PlatformDashboardResponse(BaseModel):
    organizations: int
    students_purchased: int
    students_registered: int
    active_plans: int
    expiring_this_month: int
    feature_usage: list[FeatureUsageItem]

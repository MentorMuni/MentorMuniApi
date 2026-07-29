"""Pydantic schemas for Platform Admin portal."""

from __future__ import annotations

from datetime import date, datetime
from typing import Any, Optional

from pydantic import BaseModel, EmailStr, Field


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
    created_at: datetime

    model_config = {"from_attributes": True}


class PlatformChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str = Field(min_length=8, max_length=128)


class MessageResponse(BaseModel):
    message: str


# ----- Organizations -----


class PlatformOrganizationCreate(BaseModel):
    name: str = Field(min_length=2, max_length=255)
    code: str = Field(min_length=2, max_length=64)
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


# ----- TPO -----


class CreateTpoRequest(BaseModel):
    first_name: str = Field(min_length=1, max_length=128)
    last_name: str = Field(min_length=1, max_length=128)
    email: EmailStr
    mobile: Optional[str] = None
    username: str = Field(min_length=3, max_length=128)
    # Optional override; default = 72 hours
    activation_hours: int = Field(default=72, ge=1, le=168)


class UpdateTpoRequest(BaseModel):
    """
    Change TPO details on the existing ORG_ADMIN row (same user id).

    Use when the TPO leaves: update name/email/username, force password reset
    via activation email. Org / HOD / students / dashboard data stay intact.
    """

    first_name: str = Field(min_length=1, max_length=128)
    last_name: str = Field(min_length=1, max_length=128)
    email: EmailStr
    mobile: Optional[str] = None
    username: str = Field(min_length=3, max_length=128)
    activation_hours: int = Field(default=72, ge=1, le=168)
    # When true (default), clear password and send activate link to the new email.
    reset_password: bool = True


class CreateTpoResponse(BaseModel):
    id: int
    organization_id: int
    first_name: str
    last_name: str
    email: str
    username: str
    status: str
    # Raw token returned once. Prefer email delivery; token still returned for ops fallback.
    activation_token: str
    # Full FE link (same URL embedded in the email).
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
    created_at: datetime
    activation_pending: bool


class TpoListResponse(BaseModel):
    items: list[TpoListItem]
    total: int


class ActivateTpoRequest(BaseModel):
    token: str = Field(min_length=10)
    new_password: str = Field(min_length=8, max_length=128)


# ----- Platform users -----


class PlatformUserCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    role: str = Field(pattern="^(PLATFORM_ADMIN|SUPPORT|SALES|OPERATIONS)$")


class PlatformUserUpdate(BaseModel):
    name: Optional[str] = None
    role: Optional[str] = Field(default=None, pattern="^(PLATFORM_ADMIN|SUPPORT|SALES|OPERATIONS)$")
    status: Optional[str] = Field(default=None, pattern="^(ACTIVE|INACTIVE)$")
    password: Optional[str] = Field(default=None, min_length=8, max_length=128)


class PlatformUserResponse(BaseModel):
    id: int
    name: str
    email: str
    role: str
    status: str
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

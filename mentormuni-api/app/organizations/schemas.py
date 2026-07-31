"""Organization schemas."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, EmailStr, Field


class OrganizationCreate(BaseModel):
    name: str = Field(min_length=2, max_length=255)
    code: str = Field(min_length=2, max_length=64, description="Unique short code, e.g. IIST")
    organization_type: str = Field(default="COLLEGE", pattern="^(COLLEGE|PUBLIC)$")
    contact_person: Optional[str] = None
    contact_email: Optional[EmailStr] = None
    contact_phone: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    country: Optional[str] = "India"
    # Optional: assign a plan in the same call (MentorMuni onboarding)
    plan_id: Optional[int] = None
    subscription_start_date: Optional[date] = None


class OrganizationUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=2, max_length=255)
    status: Optional[str] = Field(default=None, pattern="^(ACTIVE|SUSPENDED)$")
    contact_person: Optional[str] = None
    contact_email: Optional[EmailStr] = None
    contact_phone: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    country: Optional[str] = None


class OrganizationResponse(BaseModel):
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


class OrganizationListResponse(BaseModel):
    items: list[OrganizationResponse]
    total: int


class CollegeNameItem(BaseModel):
    """Lightweight college row for dropdowns (self-register, etc.)."""

    id: int
    name: str
    code: str

    model_config = {"from_attributes": True}


class CollegeNamesResponse(BaseModel):
    items: list[CollegeNameItem]
    total: int


class PublicDepartmentItem(BaseModel):
    id: int
    name: str
    code: str

    model_config = {"from_attributes": True}


class PublicDepartmentsResponse(BaseModel):
    departments: list[PublicDepartmentItem]


class AssignSubscriptionRequest(BaseModel):
    plan_id: int
    start_date: Optional[date] = None
    student_limit: Optional[int] = Field(default=None, ge=1)


class OrganizationSubscriptionResponse(BaseModel):
    id: int
    organization_id: int
    plan_id: int
    plan_name: Optional[str] = None
    start_date: date
    end_date: date
    student_limit: int
    status: str
    created_at: datetime

    model_config = {"from_attributes": True}


class SubscriptionPlanResponse(BaseModel):
    id: int
    plan_name: str
    plan_type: str
    duration_months: int
    max_students: int
    price: Decimal
    status: str
    created_at: datetime

    model_config = {"from_attributes": True}

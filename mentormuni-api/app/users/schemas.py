"""User schemas."""

from __future__ import annotations

from datetime import datetime
from typing import Optional, Union

from pydantic import BaseModel, EmailStr, Field


class UserCreate(BaseModel):
    """
    Create TPO / HOD / Student.

    role_code: ORG_ADMIN | DEPARTMENT_ADMIN | STUDENT
    organization_id optional for self-register (resolved from organization_code).
    """

    first_name: str = Field(min_length=1, max_length=128)
    last_name: str = Field(min_length=1, max_length=128)
    email: EmailStr
    mobile: Optional[str] = None
    username: str = Field(min_length=3, max_length=128)
    password: Optional[str] = Field(
        default=None,
        min_length=8,
        max_length=128,
        description="Required for STUDENT (self-set). Omit for HOD invite (INVITED + email).",
    )
    role_code: str = Field(pattern="^(ORG_ADMIN|DEPARTMENT_ADMIN|STUDENT)$")
    organization_id: Optional[int] = None
    organization_code: Optional[str] = None
    department_id: Optional[int] = None
    # B2C individual: set true to force MentorMuni Public + ACTIVE
    individual: bool = False
    activation_hours: int = Field(default=72, ge=1, le=168)


class StudentRegisterRequest(BaseModel):
    """
    Public self-enroll (login → Enroll) or legacy password signup.

    FE enroll body:
      organization_code, department_id, name, email, roll_number, phone
    Legacy (still accepted):
      first_name, last_name, username, password, …
    """

    email: EmailStr
    department_id: int
    organization_id: Optional[int] = None
    organization_code: Optional[str] = None

    # Preferred enroll fields
    name: Optional[str] = Field(default=None, min_length=1, max_length=256)
    roll_number: Optional[str] = Field(default=None, max_length=64)
    phone: Optional[str] = Field(default=None, max_length=32)
    mobile: Optional[str] = Field(default=None, max_length=32)

    # Legacy fields (optional when using name + no password)
    first_name: Optional[str] = Field(default=None, min_length=1, max_length=128)
    last_name: Optional[str] = Field(default=None, min_length=1, max_length=128)
    username: Optional[str] = Field(default=None, min_length=3, max_length=128)
    password: Optional[str] = Field(default=None, min_length=8, max_length=128)
    batch_year: Optional[int] = Field(default=None, ge=1990, le=2100)


class UserInviteResponse(BaseModel):
    """HOD invite result (includes activation token when email skipped/fails)."""

    user: UserResponse
    email_sent: bool = False
    activation_token: Optional[str] = None
    activation_url: Optional[str] = None
    message: str = ""


class UserImportResult(BaseModel):
    created: int
    skipped: int
    errors: list[str]
    items: list[UserResponse]


class UserUpdate(BaseModel):
    first_name: Optional[str] = Field(default=None, min_length=1, max_length=128)
    last_name: Optional[str] = Field(default=None, min_length=1, max_length=128)
    mobile: Optional[str] = None
    department_id: Optional[int] = None
    status: Optional[str] = Field(
        default=None,
        pattern="^(PENDING|ACTIVE|REJECTED|BLOCKED|INVITED)$",
    )


class UserResponse(BaseModel):
    id: int
    organization_id: int
    department_id: Optional[int] = None
    role_id: int
    role_code: Optional[str] = None
    first_name: str
    last_name: str
    email: str
    mobile: Optional[str] = None
    username: str
    status: str
    roll_number: Optional[str] = None
    batch_year: Optional[int] = None
    approved_by: Optional[int] = None
    approved_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class UserListResponse(BaseModel):
    items: list[UserResponse]
    total: int

"""Auth request/response schemas — Org Portal FE contract."""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr, Field


class LoginRequest(BaseModel):
    # Login with email OR username
    email: Optional[EmailStr] = None
    username: Optional[str] = None
    password: str = Field(min_length=1)
    # Optional: scope login to a tenant (recommended for multi-tenant)
    organization_code: Optional[str] = None
    # organization | student — enforces role + tenant rules per portal
    portal: Optional[str] = Field(default=None, max_length=32)


class MeResponse(BaseModel):
    """Session user for Org Portal (login.user + GET /auth/me)."""

    id: int
    name: str
    email: str
    # FE-preferred: TPO | HOD | STUDENT | VIEWER
    role: str
    # DB role_code: ORG_ADMIN | DEPARTMENT_ADMIN | STUDENT
    role_code: str
    role_name: str = ""
    # DEPARTMENT_ADMIN only: HOD | PLACEMENT_COORDINATOR (display)
    dept_admin_title: Optional[str] = None
    role_label: str = ""
    organization_id: int
    organization_name: str
    organization_code: str
    organization_type: str = "COLLEGE"
    # Convenience flag for FE: True when organization_type == PUBLIC
    is_individual: bool = False
    department_id: Optional[int] = None
    department_name: str = ""
    department_code: str = ""
    permissions: list[str] = Field(default_factory=list)
    must_change_password: bool = False
    # Back-compat fields
    user_id: int
    first_name: str = ""
    last_name: str = ""
    mobile: Optional[str] = None
    username: str = ""
    status: str = "ACTIVE"
    # Individual profile (and optional college metadata for college students)
    college_name: Optional[str] = None
    course_or_branch: Optional[str] = None
    batch_year: Optional[int] = None
    roll_number: Optional[str] = None
    created_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class TokenResponse(BaseModel):
    """Login payload — JWT + session user."""

    access_token: str
    token_type: str = "bearer"
    expires_in_minutes: int
    user: MeResponse
    # Flat mirrors (older FE clients)
    user_id: int
    organization_id: int
    department_id: Optional[int] = None
    role: str
    permissions: list[str]


class ChangePasswordRequest(BaseModel):
    current_password: str = Field(min_length=1)
    new_password: str = Field(min_length=8, max_length=128)


class ForgotPasswordRequest(BaseModel):
    """
    Request a password-reset email.

    Accepts email and/or username, or a single identifier (college ID / username / email).
    """

    email: Optional[EmailStr] = None
    username: Optional[str] = Field(default=None, max_length=100)
    identifier: Optional[str] = Field(default=None, max_length=255)
    organization_code: Optional[str] = None
    # organization → Org/Mentormuni login; student → Student portal
    portal: Optional[str] = Field(default="organization", max_length=32)


class ForgotPasswordResponse(BaseModel):
    message: str
    emailed: bool = False
    reset_url: Optional[str] = None


class ResetPasswordRequest(BaseModel):
    token: str = Field(min_length=16)
    new_password: str = Field(min_length=8, max_length=128)


class ActivateAccountRequest(BaseModel):
    """Activate INVITED TPO or HOD via emailed token."""

    token: str = Field(min_length=16)
    new_password: str = Field(min_length=8, max_length=128)


class ActivateAccountResponse(BaseModel):
    message: str
    organization_code: Optional[str] = None


class MessageResponse(BaseModel):
    message: str

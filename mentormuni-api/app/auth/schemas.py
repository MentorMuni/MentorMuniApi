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
    organization_id: int
    organization_name: str
    organization_code: str
    organization_type: str = "COLLEGE"
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
    email: EmailStr
    organization_code: Optional[str] = None


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

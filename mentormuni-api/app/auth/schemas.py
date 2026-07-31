"""Auth request/response schemas."""

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


class TokenResponse(BaseModel):
    """Login payload for Org Portal FE — JWT + TenantContext fields."""

    access_token: str
    token_type: str = "bearer"
    expires_in_minutes: int
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


class MeResponse(BaseModel):
    id: int
    user_id: int
    organization_id: int
    organization_code: str
    organization_name: str
    organization_type: str
    department_id: Optional[int] = None
    department_code: Optional[str] = None
    role: str
    role_code: str
    role_name: str
    permissions: list[str]
    first_name: str
    last_name: str
    email: str
    mobile: Optional[str] = None
    username: str
    status: str
    created_at: datetime

    model_config = {"from_attributes": True}


class MessageResponse(BaseModel):
    message: str

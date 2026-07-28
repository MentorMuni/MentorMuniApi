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
    access_token: str
    token_type: str = "bearer"
    expires_in_minutes: int


class ChangePasswordRequest(BaseModel):
    current_password: str = Field(min_length=1)
    new_password: str = Field(min_length=8, max_length=128)


class MeResponse(BaseModel):
    id: int
    organization_id: int
    organization_code: str
    organization_type: str
    department_id: Optional[int] = None
    department_code: Optional[str] = None
    role_code: str
    role_name: str
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

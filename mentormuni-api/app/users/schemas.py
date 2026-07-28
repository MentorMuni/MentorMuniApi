"""User schemas."""

from __future__ import annotations

from datetime import datetime
from typing import Optional

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
    password: str = Field(min_length=8, max_length=128)
    role_code: str = Field(pattern="^(ORG_ADMIN|DEPARTMENT_ADMIN|STUDENT)$")
    organization_id: Optional[int] = None
    organization_code: Optional[str] = None
    department_id: Optional[int] = None
    # B2C individual: set true to force MentorMuni Public + ACTIVE
    individual: bool = False


class UserUpdate(BaseModel):
    first_name: Optional[str] = Field(default=None, min_length=1, max_length=128)
    last_name: Optional[str] = Field(default=None, min_length=1, max_length=128)
    mobile: Optional[str] = None
    department_id: Optional[int] = None
    status: Optional[str] = Field(
        default=None,
        pattern="^(PENDING|ACTIVE|REJECTED|BLOCKED)$",
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
    approved_by: Optional[int] = None
    approved_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class UserListResponse(BaseModel):
    items: list[UserResponse]
    total: int

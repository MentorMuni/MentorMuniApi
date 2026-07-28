"""Department schemas."""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class DepartmentCreate(BaseModel):
    name: str = Field(min_length=1, max_length=128)
    code: str = Field(min_length=1, max_length=64)
    # Optional: platform can create for any org; TPO uses their own org from JWT.
    organization_id: Optional[int] = None


class DepartmentUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=128)
    status: Optional[str] = Field(default=None, pattern="^(ACTIVE|INACTIVE)$")


class DepartmentResponse(BaseModel):
    id: int
    organization_id: int
    name: str
    code: str
    status: str
    created_at: datetime

    model_config = {"from_attributes": True}

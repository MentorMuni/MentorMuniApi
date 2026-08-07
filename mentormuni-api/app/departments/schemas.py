"""Department schemas — Org Portal FE contract."""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr, Field


class DepartmentCreate(BaseModel):
    name: str = Field(min_length=1, max_length=128)
    code: str = Field(min_length=1, max_length=64)
    # Optional: platform can create for any org; TPO uses their own org from JWT.
    organization_id: Optional[int] = None


class DepartmentUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=128)
    code: Optional[str] = Field(default=None, min_length=1, max_length=64)
    status: Optional[str] = Field(default=None, pattern="^(ACTIVE|INACTIVE)$")
    # FE may send these on save; ignored — HOD lifecycle uses /hod endpoints.
    hod_name: Optional[str] = None
    hod_email: Optional[str] = None


class DepartmentResponse(BaseModel):
    """Legacy /departments payload."""

    id: int
    organization_id: int
    name: str
    code: str
    status: str
    created_at: datetime

    model_config = {"from_attributes": True}


class MentorHistoryItem(BaseModel):
    id: str
    at: datetime
    event: str  # invited | activated | revoked | replaced | reinvited
    name: str = ""
    email: str = ""
    reason: str = ""
    replaced_by_email: str = ""


class OrgDepartmentResponse(BaseModel):
    """FE-friendly department row for /organizations/departments."""

    id: int
    organization_id: int
    name: str
    code: str
    status: str
    created_at: datetime
    hod_name: Optional[str] = None
    hod_email: Optional[str] = None
    hod_status: str = "unassigned"  # unassigned | invited | active | revoked
    coordinator_name: Optional[str] = None
    coordinator_email: Optional[str] = None
    coordinator_status: str = "unassigned"
    coordinator_invited_at: Optional[datetime] = None
    coordinator_activated_at: Optional[datetime] = None
    student_count: int = 0
    invited_at: Optional[datetime] = None
    activated_at: Optional[datetime] = None
    mentor_history: list[MentorHistoryItem] = Field(default_factory=list)
    # Present on invite responses when flattened (legacy); prefer HodLifecycleResponse
    activation_token: Optional[str] = None
    activation_url: Optional[str] = None
    emailed: Optional[bool] = None
    message: Optional[str] = None

    model_config = {"from_attributes": True}


class HodLifecycleResponse(BaseModel):
    """Invite / reinvite / revoke / replace response (FE contract)."""

    message: str
    emailed: bool = False
    activation_token: Optional[str] = None
    activation_url: Optional[str] = None
    department: OrgDepartmentResponse


class HodInviteRequest(BaseModel):
    name: str = Field(min_length=1, max_length=256)
    email: EmailStr


class HodReplaceRequest(BaseModel):
    name: str = Field(min_length=1, max_length=256)
    email: EmailStr
    reason: Optional[str] = None


class HodRevokeRequest(BaseModel):
    reason: Optional[str] = None

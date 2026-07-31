"""Schemas for /organizations/students FE contract."""

from __future__ import annotations

from datetime import datetime
from typing import Optional, Union

from pydantic import BaseModel, EmailStr, Field


class StudentInviteRequest(BaseModel):
    emails: list[EmailStr] = Field(min_length=1)
    department_id: int
    source: str = "invite"


class StudentManualCreate(BaseModel):
    name: str = Field(min_length=1, max_length=256)
    email: EmailStr
    department_id: int
    roll_number: Optional[str] = Field(default=None, max_length=64)
    batch_year: Optional[int] = Field(default=None, ge=1990, le=2100)
    source: str = "manual"


class StudentImportRow(BaseModel):
    email: EmailStr
    name: Optional[str] = None
    roll_number: Optional[str] = Field(default=None, max_length=64)
    batch_year: Optional[int] = Field(default=None, ge=1990, le=2100)


class StudentImportRequest(BaseModel):
    department_id: int
    rows: list[StudentImportRow] = Field(default_factory=list)
    csv_text: Optional[str] = None
    send_invite_email: bool = False
    source: str = "import"


class StudentPatchRequest(BaseModel):
    department_id: Optional[int] = None
    status: Optional[str] = Field(default=None, pattern="^(ACTIVE|BLOCKED|PENDING|INVITED)$")
    roll_number: Optional[str] = Field(default=None, max_length=64)
    batch_year: Optional[int] = Field(default=None, ge=1990, le=2100)
    first_name: Optional[str] = Field(default=None, min_length=1, max_length=128)
    last_name: Optional[str] = Field(default=None, min_length=1, max_length=128)


class OrgStudentResponse(BaseModel):
    id: int
    email: str
    name: str
    first_name: str
    last_name: str
    username: str
    organization_id: int
    department_id: Optional[int] = None
    department_name: Optional[str] = None
    department_code: Optional[str] = None
    roll_number: Optional[str] = None
    batch_year: Optional[int] = None
    status: str
    auth_status: str  # needs_password | ready
    source: Optional[str] = None
    created_at: datetime
    approved_at: Optional[datetime] = None
    setup_url: Optional[str] = None
    activation_token: Optional[str] = None
    message: Optional[str] = None


class OrgStudentListResponse(BaseModel):
    items: list[OrgStudentResponse]
    total: int


class OrgInviteResponse(BaseModel):
    id: int
    email: str
    name: str
    department_id: Optional[int] = None
    department_name: Optional[str] = None
    roll_number: Optional[str] = None
    batch_year: Optional[int] = None
    phone: Optional[str] = None
    mobile: Optional[str] = None
    status: str  # pending | approved | rejected
    source: Optional[str] = None
    created_at: datetime


class OrgInviteListResponse(BaseModel):
    items: list[OrgInviteResponse]
    total: int


class StudentInviteResult(BaseModel):
    created: int
    skipped: int
    errors: list[str] = Field(default_factory=list)
    items: list[OrgInviteResponse] = Field(default_factory=list)


class StudentImportResult(BaseModel):
    created: int
    updated: int = 0
    skipped: int
    errors: list[dict] = Field(default_factory=list)
    items: list[Union[OrgInviteResponse, OrgStudentResponse]] = Field(default_factory=list)


class StudentApproveResponse(BaseModel):
    student: OrgStudentResponse
    email_sent: bool = False
    emailed: bool = False
    activation_token: Optional[str] = None
    setup_url: Optional[str] = None
    message: str = ""

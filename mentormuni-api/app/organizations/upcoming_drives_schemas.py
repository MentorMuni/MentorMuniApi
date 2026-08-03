"""Upcoming placement drives schemas (Org Admin only)."""

from __future__ import annotations

from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, Field, field_validator


class UpcomingDriveCreate(BaseModel):
    company_name: str = Field(min_length=1, max_length=255)
    eligibility_criteria: str = Field(min_length=1)
    drive_date: date
    remark: Optional[str] = None

    @field_validator("company_name", "eligibility_criteria")
    @classmethod
    def strip_required(cls, value: str) -> str:
        text = str(value or "").strip()
        if not text:
            raise ValueError("field is required")
        return text

    @field_validator("remark")
    @classmethod
    def strip_remark(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        text = str(value).strip()
        return text or None


class UpcomingDriveUpdate(BaseModel):
    company_name: Optional[str] = Field(default=None, min_length=1, max_length=255)
    eligibility_criteria: Optional[str] = Field(default=None, min_length=1)
    drive_date: Optional[date] = None
    remark: Optional[str] = None

    @field_validator("company_name", "eligibility_criteria")
    @classmethod
    def strip_optional_required(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        text = str(value).strip()
        if not text:
            raise ValueError("field cannot be empty")
        return text

    @field_validator("remark")
    @classmethod
    def strip_remark(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        text = str(value).strip()
        return text or None


class UpcomingDriveResponse(BaseModel):
    id: int
    company_name: str
    eligibility_criteria: str
    drive_date: date
    remark: Optional[str] = None
    created_by: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class UpcomingDriveListResponse(BaseModel):
    items: list[UpcomingDriveResponse]

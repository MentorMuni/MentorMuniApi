"""Campus program / assessment assignment schemas."""

from __future__ import annotations

from datetime import date, datetime
from typing import Any, Optional

from pydantic import BaseModel, Field, field_validator, model_validator


FE_AUDIENCES = ("all", "department", "student")
PROGRAM_TYPES = (
    "readiness",
    "aptitude",
    "skill",
    "english",
    "technical",
    "mock_ai",
    "mock_hr",
    "competition",
    "feature",
    "custom",
)


class ProgramCreateIn(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    type: str = Field(default="custom")
    audience: str = Field(default="all", description="all | department | student")
    department_id: Optional[int] = None
    department_ids: Optional[list[int]] = None
    student_ids: list[int] = Field(default_factory=list)
    due_in_days: int = Field(default=7, ge=1, le=365)
    message: Optional[str] = None

    @field_validator("type")
    @classmethod
    def normalize_type(cls, value: str) -> str:
        code = str(value or "custom").strip().lower()
        if code not in PROGRAM_TYPES:
            return "custom"
        return code

    @field_validator("audience")
    @classmethod
    def normalize_audience(cls, value: str) -> str:
        code = str(value or "all").strip().lower()
        if code not in FE_AUDIENCES:
            raise ValueError(f"audience must be one of: {', '.join(FE_AUDIENCES)}")
        return code

    @model_validator(mode="after")
    def require_scope(self) -> "ProgramCreateIn":
        dept_ids: list[int] = []
        if self.department_ids:
            for raw in self.department_ids:
                try:
                    dept_ids.append(int(raw))
                except (TypeError, ValueError):
                    continue
        elif self.department_id is not None:
            dept_ids = [int(self.department_id)]
        dept_ids = list(dict.fromkeys(dept_ids))
        if self.audience == "department":
            if not dept_ids:
                raise ValueError("department_id or department_ids is required when audience=department")
            self.department_ids = dept_ids
            if self.department_id is None:
                self.department_id = dept_ids[0]
        if self.audience == "student" and not self.student_ids:
            raise ValueError("student_ids is required when audience=student")
        return self


class ProgramOut(BaseModel):
    id: int
    title: str
    type: str
    audience: str
    department_id: Optional[int] = None
    department_ids: list[int] = Field(default_factory=list)
    student_ids: list[int] = Field(default_factory=list)
    due_in_days: int = 7
    due_date: Optional[date] = None
    status: str = "active"
    delivery_status: str = "queued"
    recipients_estimated: int = 0
    message: str = ""
    created_at: Optional[datetime] = None
    created_by: Optional[int] = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class ProgramCreateResponse(BaseModel):
    program: ProgramOut
    message: str = "Program assigned."


class ProgramListResponse(BaseModel):
    items: list[ProgramOut] = Field(default_factory=list)
    total: int = 0


class ProgramDeleteResponse(BaseModel):
    id: int
    message: str = "Program removed."

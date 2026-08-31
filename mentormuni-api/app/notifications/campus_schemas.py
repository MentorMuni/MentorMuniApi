"""Campus notification schemas (TPO events / workshops / announcements)."""

from __future__ import annotations

from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, Field, field_validator, model_validator


FE_AUDIENCES = ("all", "department", "hods")
FE_KINDS = ("event", "workshop", "announcement")


def _normalize_department_ids(
    department_id: Optional[int],
    department_ids: Optional[list[int]],
) -> list[int]:
    out: list[int] = []
    if department_ids:
        for raw in department_ids:
            try:
                out.append(int(raw))
            except (TypeError, ValueError):
                continue
    elif department_id is not None:
        out.append(int(department_id))
    return list(dict.fromkeys(out))


class CampusNotificationCreate(BaseModel):
    kind: str = Field(default="announcement", description="event | workshop | announcement")
    title: str = Field(min_length=1, max_length=255)
    message: str = Field(min_length=1)
    date: Optional[date] = None
    audience: str = Field(default="all", description="all | department | hods")
    department_id: Optional[int] = None
    department_ids: Optional[list[int]] = None

    @field_validator("kind")
    @classmethod
    def normalize_kind(cls, value: str) -> str:
        code = str(value or "announcement").strip().lower()
        if code not in FE_KINDS:
            raise ValueError(f"kind must be one of: {', '.join(FE_KINDS)}")
        return code

    @field_validator("audience")
    @classmethod
    def normalize_audience(cls, value: str) -> str:
        code = str(value or "all").strip().lower()
        if code not in FE_AUDIENCES:
            raise ValueError(f"audience must be one of: {', '.join(FE_AUDIENCES)}")
        return code

    @model_validator(mode="after")
    def require_department_when_needed(self) -> "CampusNotificationCreate":
        if self.audience == "department":
            ids = _normalize_department_ids(self.department_id, self.department_ids)
            if not ids:
                raise ValueError(
                    "department_id or department_ids is required when audience=department"
                )
            self.department_ids = ids
            if self.department_id is None:
                self.department_id = ids[0]
        return self


class CampusNotificationCreateResponse(BaseModel):
    id: int
    delivery_status: str
    recipients_estimated: int
    message: str


class CampusNotificationItem(BaseModel):
    id: int
    kind: str
    title: str
    message: str
    date: Optional[date] = None
    audience: str
    department_id: Optional[int] = None
    department_ids: list[int] = Field(default_factory=list)
    created_at: datetime
    delivery_status: str
    created_by: Optional[int] = None
    recipients_estimated: int = 0


class CampusNotificationListResponse(BaseModel):
    items: list[CampusNotificationItem]
    total: int


class CampusNotificationDeleteResponse(BaseModel):
    id: int
    delivery_status: str
    message: str

"""Notification schemas."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field


class NotificationCreate(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    body: str = Field(min_length=1)
    audience: str = Field(default="ORG", pattern="^(ORG|DEPARTMENT|USERS)$")
    department_id: Optional[int] = None
    user_ids: Optional[list[int]] = None
    metadata_json: Optional[dict[str, Any]] = None


class NotificationUpdate(BaseModel):
    title: Optional[str] = Field(default=None, min_length=1, max_length=255)
    body: Optional[str] = Field(default=None, min_length=1)
    status: Optional[str] = Field(default=None, pattern="^(ACTIVE|INACTIVE)$")


class NotificationResponse(BaseModel):
    id: int
    organization_id: int
    created_by: Optional[int] = None
    title: str
    body: str
    audience: str
    department_id: Optional[int] = None
    status: str
    metadata_json: Optional[dict[str, Any]] = None
    created_at: datetime
    recipient_count: int = 0

    model_config = {"from_attributes": True}


class NotificationListResponse(BaseModel):
    items: list[NotificationResponse]
    total: int


class InboxItem(BaseModel):
    notification_id: int
    title: str
    body: str
    status: str
    read_at: Optional[datetime] = None
    created_at: datetime

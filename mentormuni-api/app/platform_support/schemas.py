from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class AttachmentIn(BaseModel):
    filename: str = Field(min_length=1, max_length=200)
    content_type: str = Field(min_length=3, max_length=64)
    data_base64: str = Field(min_length=8)


class AttachmentOut(BaseModel):
    filename: str
    content_type: str
    data_base64: str


class TicketCreateIn(BaseModel):
    subject: str = Field(min_length=4, max_length=255)
    body: str = Field(min_length=8, max_length=8000)
    source_portal: str = Field(pattern="^(student|organization)$")
    category: str = Field(default="other", max_length=32)
    attachments: list[AttachmentIn] = Field(default_factory=list, max_length=3)


class ReplyCreateIn(BaseModel):
    body: str = Field(min_length=1, max_length=8000)
    attachments: list[AttachmentIn] = Field(default_factory=list, max_length=3)


class ReplyOut(BaseModel):
    id: int
    author_kind: str
    author_label: str
    body: str
    attachments: list[AttachmentOut] = Field(default_factory=list)
    created_at: datetime


class TicketListItemOut(BaseModel):
    id: int
    subject: str
    status: str
    category: str
    organization_id: int
    organization_name: str
    organization_code: str
    source_portal: str
    reporter_role_label: str
    reply_count: int
    created_at: datetime
    updated_at: datetime
    closed_at: Optional[datetime] = None


class TicketDetailOut(TicketListItemOut):
    replies: list[ReplyOut] = Field(default_factory=list)


class TicketListOut(BaseModel):
    items: list[TicketListItemOut]
    total: int

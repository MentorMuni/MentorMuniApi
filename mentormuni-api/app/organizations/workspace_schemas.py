"""Personal Org Admin workspace (notepad) schemas."""

from __future__ import annotations

from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, Field, field_validator

WORKSPACE_KINDS = ("todo", "note", "reminder")


class WorkspaceItemCreate(BaseModel):
    text: str = Field(min_length=1)
    due_date: Optional[date] = None
    kind: str = Field(default="todo")
    done: bool = False

    @field_validator("kind")
    @classmethod
    def normalize_kind(cls, value: str) -> str:
        code = str(value or "todo").strip().lower()
        if code not in WORKSPACE_KINDS:
            raise ValueError(f"kind must be one of: {', '.join(WORKSPACE_KINDS)}")
        return code

    @field_validator("text")
    @classmethod
    def strip_text(cls, value: str) -> str:
        text = str(value or "").strip()
        if not text:
            raise ValueError("text is required")
        return text


class WorkspaceItemUpdate(BaseModel):
    text: Optional[str] = Field(default=None, min_length=1)
    due_date: Optional[date] = None
    kind: Optional[str] = None
    done: Optional[bool] = None

    @field_validator("kind")
    @classmethod
    def normalize_kind(cls, value: Optional[str]) -> Optional[str]:
        if value is None or str(value).strip() == "":
            return None
        code = str(value).strip().lower()
        if code not in WORKSPACE_KINDS:
            raise ValueError(f"kind must be one of: {', '.join(WORKSPACE_KINDS)}")
        return code

    @field_validator("text")
    @classmethod
    def strip_text(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        text = str(value).strip()
        if not text:
            raise ValueError("text cannot be empty")
        return text


class WorkspaceItemResponse(BaseModel):
    id: int
    text: str
    due_date: Optional[date] = None
    kind: str
    done: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class WorkspaceItemListResponse(BaseModel):
    items: list[WorkspaceItemResponse]

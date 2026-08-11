"""Pydantic schemas for the student White Board."""

from __future__ import annotations

from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, Field


NOTE_COLORS = ("canary", "pink", "mint", "lilac", "peach", "sky", "coral", "butter")


class NoteCreateIn(BaseModel):
    body: str = Field(min_length=1, max_length=600)
    color: str = Field(default="canary", max_length=16)
    pin_x: Optional[float] = Field(default=None, ge=0, le=92)
    pin_y: Optional[float] = Field(default=None, ge=0, le=88)
    rotation: Optional[float] = Field(default=None, ge=-16, le=16)


class NoteUpdateIn(BaseModel):
    body: Optional[str] = Field(default=None, min_length=1, max_length=600)
    color: Optional[str] = Field(default=None, max_length=16)
    pin_x: Optional[float] = Field(default=None, ge=0, le=92)
    pin_y: Optional[float] = Field(default=None, ge=0, le=88)
    rotation: Optional[float] = Field(default=None, ge=-16, le=16)


class NoteOut(BaseModel):
    id: int
    body: str
    color: str
    status: str
    board_date: date
    pin_x: float
    pin_y: float
    rotation: float
    created_at: datetime
    updated_at: datetime
    resolved_at: Optional[datetime] = None


class MentorshipActionOut(BaseModel):
    order: int
    title: str
    do_exactly: str
    why_this_works: str
    done_when: str
    timebox_minutes: int = 25
    note_ids: list[int] = Field(default_factory=list)


class MentorshipOut(BaseModel):
    id: int
    mentorship_date: date
    source_notes_date: date
    status: str
    headline: str
    greeting: str
    what_changed: str
    diagnosis: str
    actions: list[MentorshipActionOut] = Field(default_factory=list)
    callout: str
    closing: str
    source: str
    model: Optional[str] = None


class MentorshipListItemOut(BaseModel):
    id: int
    mentorship_date: date
    status: str
    headline: str
    source: str


class BoardOut(BaseModel):
    today: date
    yesterday: date
    timezone: str = "Asia/Kolkata"
    generating: bool = False
    notes: list[NoteOut] = Field(default_factory=list)
    today_mentorship: Optional[MentorshipOut] = None
    mentorships: list[MentorshipListItemOut] = Field(default_factory=list)
    yesterday_note_count: int = 0
    open_note_count: int = 0

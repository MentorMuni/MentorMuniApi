"""Updated schemas for multi-step Know Me flow (not single-payload)."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal, Optional

from pydantic import BaseModel, Field, field_validator


class PrivateCheckInStartOut(BaseModel):
    """Response to start a new check-in flow."""

    checkin_id: int
    questions: list[dict]
    total_steps: int


class PrivateCheckInStepIn(BaseModel):
    """Student response to a single question step."""

    question_key: str = Field(..., min_length=1, max_length=128)
    response_type: Literal["single_select", "multi_select", "free_text_only", "multi_select_with_text"]
    selected_ids: list[str] = Field(default_factory=list, max_length=20)
    free_text: str = Field(default="", max_length=2000)

    @field_validator("free_text")
    @classmethod
    def strip_text(cls, v: str) -> str:
        return (v or "").strip()


class BlockerItem(BaseModel):
    """A specific blocker extracted from student's responses."""

    order: int
    title: str
    student_quote: str
    mentormuni_action: str


class ActionItem(BaseModel):
    """Actionable next step converted from blocker."""

    priority: int
    action_type: str
    description: str
    tool_code: str | None = None
    duration_minutes: int | None = None


class PrivateInsightOut(BaseModel):
    """Elder-brother response to student's check-in."""

    checkin_id: int
    source: Literal["openai", "heuristic"]
    model: str | None = None

    headline: str
    what_i_hear: list[str]
    narrative: str

    blockers: list[BlockerItem]
    action_plan: list[ActionItem]

    call_to_action: str
    closing_line: str

    private_note: str = "Your answers here are private. Not shared with TPO, HOD, or campus."


class PrivateProgressMetric(BaseModel):
    """Self-reported metric for progress tracking."""

    metric_key: str
    label: str
    value_before: int | None = None
    value_after: int | None = None


class PrivateProgressOut(BaseModel):
    """Progress view for 30–45 day check-in."""

    days_since_first: int
    metrics: list[PrivateProgressMetric]
    growth_summary: str

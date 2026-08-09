"""Request/response schemas for the personal mentor APIs."""

from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel, Field


class MentorContextOut(BaseModel):
    student_name: str
    college: Optional[str] = None
    department: Optional[str] = None
    week_status: Optional[str] = None
    overall_score: Optional[float] = None
    scores_by_tool: dict[str, float] = Field(default_factory=dict)
    top_strengths: list[str] = Field(default_factory=list)
    top_weaknesses: list[str] = Field(default_factory=list)
    plan_status: Optional[str] = None
    plan_summary: Optional[str] = None
    next_drive: Optional[dict[str, Any]] = None
    recent_coding: list[dict[str, Any]] = Field(default_factory=list)
    greeting_hint: str = "Ask me anything about your placement prep."


class MentorVoiceSessionRequest(BaseModel):
    """Optional voice override. Student context is loaded server-side."""

    voice: Optional[str] = Field(
        default=None,
        max_length=32,
        description="Male Realtime voice: ash, echo, verse, cedar. Default ash.",
    )


class MentorVoiceSessionResponse(BaseModel):
    client_secret: str
    expires_at: int
    model: str
    voice: str
    student_name: str
    instructions_preview: str
    realtime_calls_url: str = "https://api.openai.com/v1/realtime/calls"
    session_type: str = "realtime"
    context_used: dict[str, Any] = Field(default_factory=dict)

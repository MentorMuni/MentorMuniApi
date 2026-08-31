"""Pydantic schemas for student roadmap APIs."""

from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel, Field


class CompleteStepRequest(BaseModel):
    score: Optional[float] = Field(default=None, ge=0, le=100)
    label: Optional[str] = Field(default=None, max_length=255)
    technical_score: Optional[int] = Field(default=None, ge=0, le=100)
    communication_score: Optional[int] = Field(default=None, ge=0, le=100)
    strengths: list[str] = Field(default_factory=list)
    weaknesses: list[str] = Field(default_factory=list)
    recommendations: list[Any] = Field(default_factory=list)
    raw: Optional[dict[str, Any]] = None


class RoadmapStepOut(BaseModel):
    tool_code: str
    order: int
    title: str
    minutes: int
    status: str
    score: Optional[float] = None
    label: Optional[str] = None
    technical_score: Optional[int] = None
    communication_score: Optional[int] = None
    strengths: list[Any] = Field(default_factory=list)
    weaknesses: list[Any] = Field(default_factory=list)
    recommendations: list[Any] = Field(default_factory=list)
    href: str
    completed_at: Optional[str] = None


class RoadmapOut(BaseModel):
    week_number: int
    week_status: str
    completed_count: int
    total_count: int
    current_tool_code: Optional[str] = None
    plan_available: bool = False
    plan_status: Optional[str] = None
    steps: list[RoadmapStepOut]


class BaselinePathRequest(BaseModel):
    path: str = Field(..., pattern="^(fast_track|standard|foundation)$")


class AnalysisOut(BaseModel):
    week_number: int
    week_status: str
    overall_score: Optional[float] = None
    scores_by_tool: dict[str, float] = Field(default_factory=dict)
    top_strengths: list[str] = Field(default_factory=list)
    top_weaknesses: list[str] = Field(default_factory=list)
    recommendations: list[str] = Field(default_factory=list)
    voice_avg: Optional[dict[str, Optional[float]]] = None


class AssessmentResultOut(BaseModel):
    id: int
    tool_code: str
    attempt_number: int
    score: Optional[float] = None
    label: Optional[str] = None
    technical_score: Optional[int] = None
    communication_score: Optional[int] = None
    strengths: list[Any] = Field(default_factory=list)
    weaknesses: list[Any] = Field(default_factory=list)
    recommendations: list[Any] = Field(default_factory=list)
    source: str
    created_at: Optional[str] = None


class GeneratedPlanOut(BaseModel):
    id: int
    status: str
    prompt_version: str
    model: Optional[str] = None
    summary: Optional[str] = None
    plan: Optional[dict[str, Any]] = None
    error_message: Optional[str] = None
    created_at: Optional[str] = None
    completed_at: Optional[str] = None


class ProgressActivityStepOut(BaseModel):
    tool_code: str
    title: str
    order: int
    score: Optional[float] = None
    label: Optional[str] = None
    strengths: list[Any] = Field(default_factory=list)
    weaknesses: list[Any] = Field(default_factory=list)
    completed_at: Optional[str] = None


class ProgressActivityOut(BaseModel):
    week_number: int
    week_status: str
    completed_count: int
    total_count: int
    current_tool_code: Optional[str] = None
    completed_steps: list[ProgressActivityStepOut] = Field(default_factory=list)


class LearningTopicOut(BaseModel):
    topic: str
    why: str = ""
    nearby: Optional[str] = None
    priority: int = 2
    suggested_minutes: int = 45


class ProgressLearningTopicsOut(BaseModel):
    coach_summary: str = ""
    focus_order: list[str] = Field(default_factory=lambda: ["aptitude", "skills", "interview"])
    learning_topics: dict[str, list[LearningTopicOut]] = Field(default_factory=dict)
    prompt_version: str
    model: Optional[str] = None
    status: str = "ready"
    error_message: Optional[str] = None


class ProgressOut(BaseModel):
    activity: ProgressActivityOut
    analysis: AnalysisOut
    learning_topics: Optional[ProgressLearningTopicsOut] = None

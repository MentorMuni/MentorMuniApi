"""Pydantic schemas for Student Intelligence P0 APIs."""

from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel, Field


class StudentTargetIn(BaseModel):
    target_companies: list[str] = Field(default_factory=list)
    target_tier: str = "mass_recruiter"
    target_readiness: int = 85
    starting_level: str = "some_experience"
    baseline_path: Optional[str] = None
    daily_budget_minutes: int = 25
    onboarding_completed: bool = False


class StudentTargetOut(BaseModel):
    target_companies: list[str]
    target_tier: str
    target_readiness: int
    starting_level: str
    baseline_path: Optional[str] = None
    daily_budget_minutes: int = 25
    onboarding_completed: bool = False
    baseline_sprint_start_date: Optional[str] = None


class AttemptIn(BaseModel):
    tool_code: str
    topic_nodes: list[str] = Field(default_factory=list)
    modality: Optional[str] = None
    difficulty: Optional[int] = None
    score: Optional[float] = None
    accuracy: Optional[float] = None
    time_taken_s: Optional[int] = None
    technical_score: Optional[float] = None
    communication_score: Optional[float] = None
    mistakes: list[str] = Field(default_factory=list)
    attempt_number: Optional[int] = 1
    widget_spec: Optional[dict[str, Any]] = None
    item_embeddings: Optional[list[float]] = None
    transcript_ref: Optional[str] = None
    completed_at: Optional[str] = None
    within_time: bool = True
    pool: Optional[str] = None  # NEW | RETRY | VERIFY — default inferred


class TaskCompleteIn(BaseModel):
    local_date: Optional[str] = None
    plan_id: Optional[int] = None
    score: Optional[float] = None
    text_hash: Optional[str] = None
    source: Optional[str] = "manual"
    tool_code: Optional[str] = None
    topic_nodes: list[str] = Field(default_factory=list)


class TaskSkipIn(BaseModel):
    local_date: Optional[str] = None
    plan_id: Optional[int] = None
    reason: Optional[str] = "manual"
    text_hash: Optional[str] = None


class ReadinessHistoryPoint(BaseModel):
    date: str
    overall: Optional[int] = None
    coverage: Optional[float] = None
    measured_pillars: Optional[int] = None
    weakest_pillar: Optional[str] = None
    pillars: dict[str, Optional[float]] = Field(default_factory=dict)


class ReadinessHistoryOut(BaseModel):
    student_id: int
    days: int = 30
    points: list[ReadinessHistoryPoint] = Field(default_factory=list)


class PerformanceInsightsOut(BaseModel):
    focus_pillar: Optional[str] = None
    weakest_pillar: Optional[str] = None
    top_strengths: list[str] = Field(default_factory=list)
    top_weaknesses: list[str] = Field(default_factory=list)
    strong_pillars: list[dict[str, Any]] = Field(default_factory=list)
    weak_pillars: list[dict[str, Any]] = Field(default_factory=list)
    source: str = "cumulative"
    updated_from: list[str] = Field(default_factory=list)


class GatesSummaryOut(BaseModel):
    cleared_count: int = 0
    total_count: int = 0
    cleared: list[dict[str, Any]] = Field(default_factory=list)
    next_targets: list[dict[str, Any]] = Field(default_factory=list)


class DailyMissionSummaryOut(BaseModel):
    mode: str = "baseline"  # baseline | awaiting_plan | plan | intelligence
    title: str = ""
    focus_pillar: Optional[str] = None
    tasks_total: int = 0
    tasks_done: int = 0
    current_task: Optional[dict[str, Any]] = None
    day_in_plan: Optional[int] = None
    theme: Optional[str] = None
    week_ordinal: Optional[int] = None
    horizon: Optional[int] = None
    plan_id: Optional[int] = None
    fallback_reason: Optional[str] = None
    plan_day_empty: bool = False


class PlanProgressOut(BaseModel):
    """Live placement-plan progress after Week-1 baseline."""

    mode: str = "baseline"
    day_in_plan: Optional[int] = None
    horizon: Optional[int] = None
    week_ordinal: Optional[int] = None
    theme: Optional[str] = None
    tasks_done: int = 0
    tasks_total: int = 0
    title: str = ""
    plan_id: Optional[int] = None
    fallback_reason: Optional[str] = None
    plan_day_empty: bool = False


class StudentPerformanceDashboardOut(BaseModel):
    readiness: dict[str, Any]
    history: ReadinessHistoryOut
    insights: PerformanceInsightsOut
    target: StudentTargetOut
    roadmap: dict[str, Any]
    gates_summary: GatesSummaryOut
    daily_mission: DailyMissionSummaryOut
    plan_progress: Optional[PlanProgressOut] = None

"""Schemas for organization performance analytics + AI insight."""

from __future__ import annotations

from typing import Any, Literal, Optional

from pydantic import BaseModel, Field


class GapStrengthItem(BaseModel):
    label: str
    count: int = 0
    share_pct: float = 0  # % of scored students showing this theme


class ToolCoverageItem(BaseModel):
    tool: str
    label: str
    completed: int = 0
    in_progress: int = 0
    remaining: int = 0
    total: int = 0
    pct: float = 0


class ClarityBoard(BaseModel):
    """Deterministic situation board — always derived from aggregates."""

    going_well: list[str] = Field(default_factory=list)
    concerns: list[str] = Field(default_factory=list)
    priorities: list[str] = Field(default_factory=list)
    status: Literal["healthy", "watch", "critical"] = "watch"


class DeptPerformanceRow(BaseModel):
    id: int
    code: Optional[str] = None
    name: str
    students: int = 0
    scored_students: int = 0
    coverage_pct: float = 0
    avg_readiness: Optional[float] = None
    avg_mock: Optional[float] = None
    strong: int = 0
    mid: int = 0
    weak: int = 0
    active_7d: int = 0
    inactive_14d: int = 0
    never_started: int = 0
    avg_tests_done: Optional[float] = None
    top_gap: Optional[str] = None
    hod_status: Optional[str] = None


class PillarAverages(BaseModel):
    aptitude: Optional[float] = None
    skills: Optional[float] = None
    interview: Optional[float] = None
    snap: Optional[float] = None
    communication: Optional[float] = None
    technical: Optional[float] = None
    shortlist: Optional[float] = None


class RankedStudent(BaseModel):
    rank: int
    id: int
    name: str
    email: Optional[str] = None
    department_id: Optional[int] = None
    department_name: Optional[str] = None
    score: Optional[float] = None
    readiness: Optional[float] = None
    strength: Optional[str] = None
    weakness: Optional[str] = None
    best_area: Optional[str] = None
    tests_done: int = 0
    tests_remaining: int = 0
    progress_level: int = 0
    activity_status: str = "never"


class AreaBoard(BaseModel):
    area: str
    label: str
    description: str = ""
    students_scored: int = 0
    avg_score: Optional[float] = None
    top: list[RankedStudent] = Field(default_factory=list)
    less_prepared: list[RankedStudent] = Field(default_factory=list)


class LevelFunnelItem(BaseModel):
    level: int
    label: str
    tool: str
    reached_or_beyond: int = 0
    completed: int = 0
    pct_completed: float = 0


class TestsAggregate(BaseModel):
    tools_total: int = 8
    avg_tests_done: float = 0
    avg_tests_remaining: float = 0
    students_all_done: int = 0
    students_none_done: int = 0
    total_completions: int = 0
    total_remaining: int = 0


class LeaderboardEntry(BaseModel):
    id: int
    name: str
    department_id: Optional[int] = None
    department_name: Optional[str] = None
    readiness: float = 0
    mock_score: Optional[float] = None
    strength: Optional[str] = None
    weakness: Optional[str] = None
    best_area: Optional[str] = None
    activities: int = 0
    tests_done: int = 0
    progress_level: int = 0
    last_active_at: Optional[str] = None
    days_inactive: Optional[int] = None


class AreaLeader(BaseModel):
    area: str
    label: str
    student_id: Optional[int] = None
    student_name: Optional[str] = None
    department_name: Optional[str] = None
    score: Optional[float] = None


class StudentScorecard(BaseModel):
    id: int
    name: str
    email: Optional[str] = None
    department_id: Optional[int] = None
    department_name: Optional[str] = None
    readiness: Optional[float] = None
    mock_score: Optional[float] = None
    technical_score: Optional[float] = None
    communication_score: Optional[float] = None
    shortlist_score: Optional[float] = None
    scores_by_tool: dict[str, float] = Field(default_factory=dict)
    step_status_by_tool: dict[str, str] = Field(default_factory=dict)
    strength: Optional[str] = None
    weakness: Optional[str] = None
    strengths: list[str] = Field(default_factory=list)
    weaknesses: list[str] = Field(default_factory=list)
    activities: int = 0
    attempts: int = 0
    tests_done: int = 0
    tests_in_progress: int = 0
    tests_remaining: int = 0
    progress_level: int = 0
    progress_pct: float = 0
    week_status: Optional[str] = None
    last_active_at: Optional[str] = None
    days_inactive: Optional[int] = None
    activity_status: Literal["active", "idle", "inactive", "never"] = "never"
    best_area: Optional[str] = None


class PerformanceBands(BaseModel):
    strong: int = 0
    mid: int = 0
    weak: int = 0
    unscored: int = 0


class PerformanceSummaryOut(BaseModel):
    scope: Literal["organization", "department"]
    organization_id: int
    department_id: Optional[int] = None
    students_total: int = 0
    students_scored: int = 0
    coverage_pct: float = 0
    drive_ready_pct: float = 0
    drive_ready_of_scored_pct: float = 0
    filtered_department_id: Optional[int] = None
    avg_readiness: Optional[float] = None
    avg_mock: Optional[float] = None
    bands: PerformanceBands = Field(default_factory=PerformanceBands)
    pillars: PillarAverages = Field(default_factory=PillarAverages)
    tool_coverage: list[ToolCoverageItem] = Field(default_factory=list)
    level_funnel: list[LevelFunnelItem] = Field(default_factory=list)
    tests: TestsAggregate = Field(default_factory=TestsAggregate)
    top_gaps: list[GapStrengthItem] = Field(default_factory=list)
    top_strengths: list[GapStrengthItem] = Field(default_factory=list)
    by_department: list[DeptPerformanceRow] = Field(default_factory=list)
    leaders: list[LeaderboardEntry] = Field(default_factory=list)
    at_risk: list[LeaderboardEntry] = Field(default_factory=list)
    area_leaders: list[AreaLeader] = Field(default_factory=list)
    area_boards: list[AreaBoard] = Field(default_factory=list)
    clarity: ClarityBoard = Field(default_factory=ClarityBoard)
    board_limit: int = 10
    active_7d: int = 0
    idle_count: int = 0
    inactive_14d: int = 0
    never_started: int = 0
    pending_invites: int = 0
    upcoming_drives: int = 0
    hod_gaps: int = 0
    generated_at: str
    # Included so FE can skip a second /scorecards call (same pipeline).
    scorecards: list[StudentScorecard] = Field(default_factory=list)


class ScorecardListOut(BaseModel):
    scope: Literal["organization", "department"]
    total: int
    items: list[StudentScorecard] = Field(default_factory=list)


class InsightRequest(BaseModel):
    include_leaderboard: bool = True
    max_actions: int = Field(default=5, ge=3, le=8)
    locale: str = Field(default="en-IN", max_length=16)
    department_id: Optional[int] = Field(
        default=None,
        description="Optional TPO department filter for campus insight",
    )
    focus_area: Optional[str] = Field(
        default=None,
        description="Optional area focus: overall|aptitude|skills|interview|communication|technical|shortlist|snap",
    )


class InsightPayload(BaseModel):
    summary: str
    going_well: list[str] = Field(default_factory=list)
    concerns: list[str] = Field(default_factory=list)
    actions: list[str] = Field(default_factory=list)
    shortlist_notes: list[str] = Field(default_factory=list)


class InsightOut(BaseModel):
    ok: bool = True
    source: Literal["openai", "heuristic"] = "openai"
    model: Optional[str] = None
    generated_at: str
    cache_ttl_seconds: int = 900
    organization_id: int
    department_id: Optional[int] = None
    scope: Literal["organization", "department"]
    metrics: dict[str, Any] = Field(default_factory=dict)
    insight: InsightPayload

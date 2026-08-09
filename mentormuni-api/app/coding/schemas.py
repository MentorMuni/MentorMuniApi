"""Student-safe Pydantic schemas for coding assessment Phase 3 (no execution)."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field


class AssessmentSummaryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    slug: str
    title: str
    difficulty: Optional[str] = None
    duration_minutes: int
    status: str
    company_key: Optional[str] = None
    company_name: Optional[str] = None
    role_name: Optional[str] = None
    # Student-safe placement context (never evidence_json / raw confidence)
    placement_blurb: Optional[str] = None
    relevance_label: Optional[str] = None
    topic: Optional[str] = None
    pattern: Optional[str] = None
    why_this_matters: Optional[str] = None
    allowed_languages: list[str] = Field(default_factory=list)
    problem_count: int = 0


class AssessmentListOut(BaseModel):
    items: list[AssessmentSummaryOut]
    company_key: Optional[str] = None


class SubmissionSummaryOut(BaseModel):
    """Past-result list row (no source / hidden I/O)."""

    id: int
    attempt_id: int
    assessment_id: int
    assessment_slug: Optional[str] = None
    assessment_title: Optional[str] = None
    problem_id: int
    problem_title: Optional[str] = None
    company_name: Optional[str] = None
    role_name: Optional[str] = None
    language_code: str
    execution_status: str
    verdict: Optional[str] = None
    analysis_status: str
    official_score: Optional[float] = None
    submitted_at: datetime


class SubmissionListOut(BaseModel):
    items: list[SubmissionSummaryOut]


class AttemptProblemSummaryOut(BaseModel):
    problem_id: int
    problem_version_id: int
    order_index: int
    points: float
    title: str
    difficulty: str
    topic: Optional[str] = None
    pattern: Optional[str] = None
    company_name: Optional[str] = None
    role_name: Optional[str] = None


class AttemptOut(BaseModel):
    id: int
    assessment_id: int
    assessment_slug: str
    assessment_title: str
    status: str
    starts_at: datetime
    ends_at: Optional[datetime] = None
    submitted_at: Optional[datetime] = None
    server_now: datetime
    seconds_remaining: Optional[int] = None
    is_expired: bool
    company_name: Optional[str] = None
    role_name: Optional[str] = None
    placement_blurb: Optional[str] = None
    relevance_label: Optional[str] = None
    why_this_matters: Optional[str] = None
    allowed_languages: list[str] = Field(default_factory=list)
    problems: list[AttemptProblemSummaryOut] = Field(default_factory=list)


class ProblemExampleOut(BaseModel):
    input: str
    output: str
    explanation: Optional[str] = None


class AttemptProblemOut(BaseModel):
    attempt_id: int
    problem_id: int
    problem_version_id: int
    version_number: int
    title: str
    description: str
    difficulty: str
    topic: Optional[str] = None
    subtopic: Optional[str] = None
    pattern: Optional[str] = None
    company_name: Optional[str] = None
    role_name: Optional[str] = None
    constraints_text: Optional[str] = None
    input_format: Optional[str] = None
    output_format: Optional[str] = None
    examples: list[ProblemExampleOut] = Field(default_factory=list)
    concepts: list[str] = Field(default_factory=list)
    starter_code_by_language: dict[str, str] = Field(default_factory=dict)
    allowed_languages: list[str] = Field(default_factory=list)
    time_limit_ms: Optional[int] = None
    memory_limit_kb: Optional[int] = None
    points: float
    order_index: int
    attempt_status: str
    ends_at: Optional[datetime] = None
    server_now: datetime
    seconds_remaining: Optional[int] = None
    is_expired: bool


class DraftUpsertRequest(BaseModel):
    language_code: str = Field(min_length=1, max_length=32)
    source_code: str = Field(default="")


class DraftOut(BaseModel):
    id: int
    attempt_id: int
    problem_id: int
    problem_version_id: int
    language_code: str
    source_code: str
    updated_at: datetime
    created_at: datetime


class RunCreateRequest(BaseModel):
    attempt_id: int
    problem_id: int
    language_code: str = Field(min_length=1, max_length=32)
    source_code: str = Field(default="")


class RunCaseResultOut(BaseModel):
    index: int
    status: str
    verdict: Optional[str] = None
    execution_time_ms: Optional[int] = None
    memory_used_kb: Optional[int] = None
    error_type: Optional[str] = None
    compile_output: Optional[str] = None
    stderr: Optional[str] = None


class RunOut(BaseModel):
    id: int
    job_id: Optional[int] = None
    attempt_id: int
    problem_id: int
    problem_version_id: int
    language_code: str
    execution_status: str
    verdict: Optional[str] = None
    passed_count: int = 0
    total_count: int = 0
    execution_time_ms: Optional[int] = None
    memory_used_kb: Optional[int] = None
    cases: list[RunCaseResultOut] = Field(default_factory=list)
    created_at: datetime
    # Never includes hidden tests / reference solutions / official score


class SubmissionCreateRequest(BaseModel):
    attempt_id: int
    problem_id: int
    language_code: str = Field(min_length=1, max_length=32)
    source_code: str = Field(default="")


class SubmissionTestResultOut(BaseModel):
    """Student-safe test outcome. Hidden cases never include I/O."""

    index: int
    hidden: bool
    status: str
    weight: float = 1.0
    execution_time_ms: Optional[int] = None
    memory_used_kb: Optional[int] = None
    error_type: Optional[str] = None
    # Only for public cases:
    actual_output: Optional[str] = None


class SubmissionOut(BaseModel):
    id: int
    job_id: Optional[int] = None
    attempt_id: int
    assessment_id: int
    assessment_title: Optional[str] = None
    problem_id: int
    problem_title: Optional[str] = None
    problem_version_id: int
    company_name: Optional[str] = None
    role_name: Optional[str] = None
    language_code: str
    execution_status: str
    verdict: Optional[str] = None
    analysis_status: str
    # Official grade from weighted tests only
    official_score: Optional[float] = None
    passed_count: int = 0
    total_count: int = 0
    public_passed_count: int = 0
    public_total_count: int = 0
    hidden_passed_count: int = 0
    hidden_total_count: int = 0
    execution_time_ms: Optional[int] = None
    memory_used_kb: Optional[int] = None
    test_results: list[SubmissionTestResultOut] = Field(default_factory=list)
    submitted_at: datetime
    created_at: datetime
    # Never includes source_code / hidden I/O / reference solutions / coaching as grade


class ConstraintAwarenessOut(BaseModel):
    understood_constraints: Optional[bool] = None
    complexity_appropriate_for_constraints: Optional[bool] = None
    missed_scalable_approach: Optional[bool] = None
    notes: Optional[str] = None


class AnalysisOut(BaseModel):
    """Coaching analysis — separate from official_score."""

    submission_id: int
    analysis_status: str
    prompt_version: Optional[str] = None
    overall_coaching_score: Optional[float] = None
    correctness_coaching_score: Optional[float] = None
    approach_score: Optional[float] = None
    complexity_score: Optional[float] = None
    code_quality_score: Optional[float] = None
    edge_case_score: Optional[float] = None
    constraint_awareness: Optional[ConstraintAwarenessOut] = None
    detected_approach: Optional[str] = None
    time_complexity: Optional[str] = None
    space_complexity: Optional[str] = None
    beginner_explanation: Optional[str] = None
    mistakes: list[dict[str, Any]] = Field(default_factory=list)
    better_approach: Optional[dict[str, Any]] = None
    strengths: list[str] = Field(default_factory=list)
    learning_gaps: list[str] = Field(default_factory=list)
    next_learning_focus: list[str] = Field(default_factory=list)
    # Explicit separation for UI
    official_score: Optional[float] = None
    official_verdict: Optional[str] = None


# Internal snapshot shape stored on coding_attempt_snapshots (not a public API model detail)
class SnapshotProblem(BaseModel):
    problem_id: int
    problem_version_id: int
    version_number: int
    order_index: int
    points: float
    title: str
    difficulty: str
    topic: Optional[str] = None
    pattern: Optional[str] = None
    company_name: Optional[str] = None
    role_name: Optional[str] = None


class AttemptSnapshotPayload(BaseModel):
    assessment_id: int
    assessment_slug: str
    assessment_title: str
    duration_minutes: int
    allowed_languages: list[str]
    company_key: Optional[str] = None
    company_name: Optional[str] = None
    role_name: Optional[str] = None
    placement_blurb: Optional[str] = None
    relevance_label: Optional[str] = None
    why_this_matters: Optional[str] = None
    difficulty: Optional[str] = None
    problems: list[SnapshotProblem]
    # Intentionally omit evidence_json / private intel

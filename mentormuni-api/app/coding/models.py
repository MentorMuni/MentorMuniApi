"""ORM models for the coding assessment domain."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.common.database.base import Base


class CodingLanguage(Base):
    __tablename__ = "coding_languages"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(String(32), nullable=False, unique=True, index=True)
    display_name: Mapped[str] = mapped_column(String(64), nullable=False)
    judge0_language_id: Mapped[int] = mapped_column(Integer, nullable=False)
    version_label: Mapped[str] = mapped_column(String(64), nullable=False, server_default="")
    file_extension: Mapped[str] = mapped_column(String(16), nullable=False)
    time_multiplier: Mapped[float] = mapped_column(Float, nullable=False, server_default="1")
    default_memory_limit_kb: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    starter_template: Mapped[str] = mapped_column(Text, nullable=False, server_default="")
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="true")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )


class CodingProblem(Base):
    """Mutable problem head; statement/tests live on immutable versions."""

    __tablename__ = "coding_problems"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    slug: Mapped[str] = mapped_column(String(160), nullable=False, unique=True, index=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, server_default="draft", index=True)
    current_version_id: Mapped[Optional[int]] = mapped_column(
        BigInteger,
        ForeignKey("coding_problem_versions.id", ondelete="SET NULL", use_alter=True, name="fk_coding_problems_current_version"),
        nullable=True,
    )

    # Company / role awareness (schema ready; no generation pipeline)
    company_key: Mapped[Optional[str]] = mapped_column(String(160), nullable=True, index=True)
    company_name: Mapped[Optional[str]] = mapped_column(String(160), nullable=True)
    role_key: Mapped[Optional[str]] = mapped_column(String(160), nullable=True)
    role_name: Mapped[Optional[str]] = mapped_column(String(160), nullable=True)
    difficulty: Mapped[Optional[str]] = mapped_column(String(32), nullable=True, index=True)
    topic: Mapped[Optional[str]] = mapped_column(String(80), nullable=True, index=True)
    subtopic: Mapped[Optional[str]] = mapped_column(String(80), nullable=True)
    pattern: Mapped[Optional[str]] = mapped_column(String(80), nullable=True)
    evidence_confidence: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    evidence_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    evidence_json: Mapped[Optional[dict[str, Any]]] = mapped_column(JSONB, nullable=True)

    # Content-bank pipeline metadata (generation → validation → approval → publish)
    prompt_version: Mapped[Optional[str]] = mapped_column(String(64), nullable=True, index=True)
    generation_model: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    generation_run_id: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True, index=True)
    quality_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    validation_summary_json: Mapped[Optional[dict[str, Any]]] = mapped_column(JSONB, nullable=True)
    approved_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    approved_by: Mapped[Optional[str]] = mapped_column(String(160), nullable=True)
    published_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    rejected_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    content_fingerprint: Mapped[Optional[str]] = mapped_column(String(64), nullable=True, index=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    versions: Mapped[list[CodingProblemVersion]] = relationship(
        "CodingProblemVersion",
        back_populates="problem",
        foreign_keys="CodingProblemVersion.problem_id",
        cascade="all, delete-orphan",
    )


class CodingProblemVersion(Base):
    """Immutable snapshot of a problem statement + scoring policy."""

    __tablename__ = "coding_problem_versions"
    __table_args__ = (
        UniqueConstraint("problem_id", "version_number", name="uq_coding_problem_versions_problem_ver"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    problem_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("coding_problems.id", ondelete="CASCADE"), nullable=False, index=True
    )
    version_number: Mapped[int] = mapped_column(Integer, nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    difficulty: Mapped[str] = mapped_column(String(32), nullable=False)
    topic: Mapped[Optional[str]] = mapped_column(String(80), nullable=True)
    subtopic: Mapped[Optional[str]] = mapped_column(String(80), nullable=True)
    pattern: Mapped[Optional[str]] = mapped_column(String(80), nullable=True)
    constraints_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    input_format: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    output_format: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    examples_json: Mapped[list[Any]] = mapped_column(JSONB, nullable=False, server_default="[]")
    explanation_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    expected_time_complexity: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    expected_space_complexity: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    expected_approach: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    concepts_json: Mapped[list[Any]] = mapped_column(JSONB, nullable=False, server_default="[]")
    starter_code_by_language: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, server_default="{}"
    )
    supported_languages_json: Mapped[list[Any]] = mapped_column(
        JSONB, nullable=False, server_default='["python", "cpp", "java"]'
    )
    # Weight policy hints (actual weights live on test cases); e.g. {"public_share": 0.2, "hidden_share": 0.8}
    weight_policy_json: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, server_default="{}"
    )
    generation_payload_json: Mapped[Optional[dict[str, Any]]] = mapped_column(JSONB, nullable=True)
    time_limit_ms: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    memory_limit_kb: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    problem: Mapped[CodingProblem] = relationship(
        "CodingProblem",
        back_populates="versions",
        foreign_keys=[problem_id],
    )
    test_cases: Mapped[list[CodingTestCase]] = relationship(
        "CodingTestCase",
        back_populates="problem_version",
        cascade="all, delete-orphan",
    )
    reference_solutions: Mapped[list[CodingReferenceSolution]] = relationship(
        "CodingReferenceSolution",
        back_populates="problem_version",
        cascade="all, delete-orphan",
    )


class CodingReferenceSolution(Base):
    """Backend-only reference solutions — never serialize to students."""

    __tablename__ = "coding_reference_solutions"
    __table_args__ = (
        UniqueConstraint(
            "problem_version_id", "language_code", name="uq_coding_ref_sol_version_lang"
        ),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    problem_version_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("coding_problem_versions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    language_code: Mapped[str] = mapped_column(String(32), nullable=False)
    source_code: Mapped[str] = mapped_column(Text, nullable=False)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    problem_version: Mapped[CodingProblemVersion] = relationship(
        "CodingProblemVersion", back_populates="reference_solutions"
    )


class CodingTestCase(Base):
    __tablename__ = "coding_test_cases"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    problem_version_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("coding_problem_versions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    input: Mapped[str] = mapped_column(Text, nullable=False)
    expected_output: Mapped[str] = mapped_column(Text, nullable=False)
    is_hidden: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false", index=True)
    weight: Mapped[float] = mapped_column(Float, nullable=False, server_default="1")
    order_index: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    # normal | boundary | min | max | duplicates | empty | adversarial | large | ...
    category: Mapped[Optional[str]] = mapped_column(String(64), nullable=True, index=True)
    execution_config: Mapped[Optional[dict[str, Any]]] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    problem_version: Mapped[CodingProblemVersion] = relationship(
        "CodingProblemVersion", back_populates="test_cases"
    )


class CodingAssessment(Base):
    __tablename__ = "coding_assessments"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    slug: Mapped[str] = mapped_column(String(160), nullable=False, unique=True, index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    organization_id: Mapped[Optional[int]] = mapped_column(
        BigInteger, ForeignKey("organizations.id", ondelete="SET NULL"), nullable=True, index=True
    )
    company_key: Mapped[Optional[str]] = mapped_column(String(160), nullable=True, index=True)
    company_name: Mapped[Optional[str]] = mapped_column(String(160), nullable=True)
    role_key: Mapped[Optional[str]] = mapped_column(String(160), nullable=True)
    role_name: Mapped[Optional[str]] = mapped_column(String(160), nullable=True)
    difficulty: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    duration_minutes: Mapped[int] = mapped_column(Integer, nullable=False, server_default="60")
    status: Mapped[str] = mapped_column(String(32), nullable=False, server_default="draft", index=True)
    allowed_languages_json: Mapped[list[Any]] = mapped_column(
        JSONB, nullable=False, server_default='["python", "cpp", "java"]'
    )
    evidence_confidence: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    evidence_json: Mapped[Optional[dict[str, Any]]] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )


class CodingAssessmentProblem(Base):
    """Live catalog mapping (mutable). Attempts freeze versions separately."""

    __tablename__ = "coding_assessment_problems"
    __table_args__ = (
        UniqueConstraint(
            "assessment_id", "problem_id", name="uq_coding_assessment_problems_assessment_problem"
        ),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    assessment_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("coding_assessments.id", ondelete="CASCADE"), nullable=False, index=True
    )
    problem_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("coding_problems.id", ondelete="CASCADE"), nullable=False, index=True
    )
    order_index: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    points: Mapped[float] = mapped_column(Float, nullable=False, server_default="100")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class CodingAttempt(Base):
    __tablename__ = "coding_attempts"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    student_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    assessment_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("coding_assessments.id", ondelete="CASCADE"), nullable=False, index=True
    )
    status: Mapped[str] = mapped_column(String(32), nullable=False, server_default="in_progress", index=True)
    starts_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    ends_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    submitted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )


class CodingAttemptSnapshot(Base):
    """Immutable assessment configuration frozen at attempt start."""

    __tablename__ = "coding_attempt_snapshots"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    attempt_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("coding_attempts.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    snapshot_json: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class CodingAttemptProblem(Base):
    """Per-attempt frozen problem versions (queryable FKs)."""

    __tablename__ = "coding_attempt_problems"
    __table_args__ = (
        UniqueConstraint(
            "attempt_id", "problem_version_id", name="uq_coding_attempt_problems_attempt_version"
        ),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    attempt_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("coding_attempts.id", ondelete="CASCADE"), nullable=False, index=True
    )
    problem_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("coding_problems.id", ondelete="CASCADE"), nullable=False, index=True
    )
    problem_version_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("coding_problem_versions.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    order_index: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    points: Mapped[float] = mapped_column(Float, nullable=False, server_default="100")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class CodingDraft(Base):
    __tablename__ = "coding_drafts"
    __table_args__ = (
        UniqueConstraint(
            "attempt_id",
            "problem_version_id",
            "language_code",
            name="uq_coding_drafts_attempt_version_lang",
        ),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    attempt_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("coding_attempts.id", ondelete="CASCADE"), nullable=False, index=True
    )
    problem_version_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("coding_problem_versions.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    language_code: Mapped[str] = mapped_column(String(32), nullable=False)
    source_code: Mapped[str] = mapped_column(Text, nullable=False, server_default="")
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class CodingRun(Base):
    """Lightweight append-only Run Code history (no AI; public tests)."""

    __tablename__ = "coding_runs"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    student_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    attempt_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("coding_attempts.id", ondelete="CASCADE"), nullable=False, index=True
    )
    problem_version_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("coding_problem_versions.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    language_code: Mapped[str] = mapped_column(String(32), nullable=False)
    source_code: Mapped[str] = mapped_column(Text, nullable=False)
    source_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    execution_status: Mapped[str] = mapped_column(
        String(32), nullable=False, server_default="queued", index=True
    )
    verdict: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    passed_count: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    total_count: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    execution_time_ms: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    memory_used_kb: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    result_summary_json: Mapped[Optional[dict[str, Any]]] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
    )


class CodingSubmission(Base):
    """Immutable student submission for official scoring."""

    __tablename__ = "coding_submissions"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    student_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    attempt_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("coding_attempts.id", ondelete="CASCADE"), nullable=False, index=True
    )
    assessment_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("coding_assessments.id", ondelete="CASCADE"), nullable=False, index=True
    )
    problem_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("coding_problems.id", ondelete="CASCADE"), nullable=False, index=True
    )
    problem_version_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("coding_problem_versions.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    language_code: Mapped[str] = mapped_column(String(32), nullable=False)
    source_code: Mapped[str] = mapped_column(Text, nullable=False)
    source_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    execution_status: Mapped[str] = mapped_column(
        String(32), nullable=False, server_default="queued", index=True
    )
    verdict: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    analysis_status: Mapped[str] = mapped_column(
        String(32), nullable=False, server_default="pending", index=True
    )
    # Official score: weighted test pass only (never AI)
    score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    execution_time_ms: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    memory_used_kb: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    submitted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )


class CodingTestResult(Base):
    __tablename__ = "coding_test_results"
    __table_args__ = (
        UniqueConstraint(
            "submission_id", "test_case_id", name="uq_coding_test_results_submission_case"
        ),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    submission_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("coding_submissions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    test_case_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("coding_test_cases.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    execution_time_ms: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    memory_used_kb: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    actual_output: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    error_type: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class CodingAiAnalysis(Base):
    """Coaching-only analysis. Never owns official submission.score."""

    __tablename__ = "coding_ai_analyses"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    submission_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("coding_submissions.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    prompt_version: Mapped[str] = mapped_column(
        String(64), nullable=False, server_default="coding_analysis_v1"
    )
    model: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    # Coaching scores (not official grade)
    overall_coaching_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    correctness_coaching_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    approach_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    complexity_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    code_quality_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    edge_case_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    # Constraint awareness (placement prep)
    understood_constraints: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)
    complexity_appropriate_for_constraints: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)
    missed_scalable_approach: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)
    constraint_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    detected_approach: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    time_complexity: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    space_complexity: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    analysis_json: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, server_default="{}")
    raw_response: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class CodingJob(Base):
    """Durable job queue claimed by CodingJobWorker (not FastAPI BackgroundTasks)."""

    __tablename__ = "coding_jobs"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    job_type: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, server_default="pending", index=True)
    student_id: Mapped[Optional[int]] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    attempt_id: Mapped[Optional[int]] = mapped_column(
        BigInteger, ForeignKey("coding_attempts.id", ondelete="SET NULL"), nullable=True, index=True
    )
    submission_id: Mapped[Optional[int]] = mapped_column(
        BigInteger, ForeignKey("coding_submissions.id", ondelete="SET NULL"), nullable=True, index=True
    )
    run_id: Mapped[Optional[int]] = mapped_column(
        BigInteger, ForeignKey("coding_runs.id", ondelete="SET NULL"), nullable=True, index=True
    )
    provider: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    provider_submission_token: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    provider_status: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    attempt_count: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    last_error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    next_retry_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    payload_json: Mapped[Optional[dict[str, Any]]] = mapped_column(JSONB, nullable=True)
    claimed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )


class CodingProblemRelevance(Base):
    """
    Many-to-many style relevance: ONE canonical problem → many company/role/round rows.
    Never duplicate the problem statement for each company.
    """

    __tablename__ = "coding_problem_relevances"
    __table_args__ = (
        UniqueConstraint(
            "problem_id",
            "company_key",
            "role_key",
            "round_key",
            name="uq_coding_problem_relevances_tuple",
        ),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    problem_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("coding_problems.id", ondelete="CASCADE"), nullable=False, index=True
    )
    company_key: Mapped[str] = mapped_column(String(160), nullable=False, index=True)
    company_name: Mapped[Optional[str]] = mapped_column(String(160), nullable=True)
    role_key: Mapped[str] = mapped_column(String(160), nullable=False, server_default="software-engineer")
    role_name: Mapped[Optional[str]] = mapped_column(String(160), nullable=True)
    round_key: Mapped[str] = mapped_column(String(64), nullable=False, server_default="coding")
    relevance: Mapped[str] = mapped_column(String(32), nullable=False, server_default="medium")  # high|medium|low
    evidence_confidence: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    evidence_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    evidence_json: Mapped[Optional[dict[str, Any]]] = mapped_column(JSONB, nullable=True)
    source_metadata_json: Mapped[Optional[dict[str, Any]]] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )


class CodingGenerationRun(Base):
    """Batch/config tracking for content-bank generation (not student execution jobs)."""

    __tablename__ = "coding_generation_runs"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, server_default="pending", index=True)
    prompt_version: Mapped[str] = mapped_column(String(64), nullable=False)
    model: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    curriculum_version: Mapped[str] = mapped_column(String(64), nullable=False, server_default="placement_v1")
    target_count: Mapped[int] = mapped_column(Integer, nullable=False, server_default="50")
    generated_count: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    config_json: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, server_default="{}")
    last_error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_by: Mapped[Optional[str]] = mapped_column(String(160), nullable=True)
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )


class CodingValidationResult(Base):
    """Append-only validation reports for a problem (or specific version)."""

    __tablename__ = "coding_validation_results"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    problem_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("coding_problems.id", ondelete="CASCADE"), nullable=False, index=True
    )
    problem_version_id: Mapped[Optional[int]] = mapped_column(
        BigInteger,
        ForeignKey("coding_problem_versions.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    generation_run_id: Mapped[Optional[int]] = mapped_column(
        BigInteger,
        ForeignKey("coding_generation_runs.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    verdict: Mapped[str] = mapped_column(String(32), nullable=False, index=True)  # pass|fail|skipped
    quality_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    checks_json: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, server_default="{}")
    errors_json: Mapped[list[Any]] = mapped_column(JSONB, nullable=False, server_default="[]")
    duplicate_of_problem_id: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
    )

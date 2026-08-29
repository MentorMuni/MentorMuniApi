"""ORM models for Student Intelligence P0 (student portal only)."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Any, Optional

from sqlalchemy import (
    BigInteger,
    Boolean,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.common.database.base import Base


class StudentAttempt(Base):
    __tablename__ = "student_attempt"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    student_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    tool_code: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    widget_spec: Mapped[Optional[dict[str, Any]]] = mapped_column(JSONB, nullable=True)
    topic_nodes: Mapped[list[str]] = mapped_column(ARRAY(Text), nullable=False, server_default="{}")
    modality: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    difficulty: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    score: Mapped[Optional[Decimal]] = mapped_column(Numeric(5, 2), nullable=True)
    accuracy: Mapped[Optional[Decimal]] = mapped_column(Numeric(5, 4), nullable=True)
    time_taken_s: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    technical_score: Mapped[Optional[Decimal]] = mapped_column(Numeric(5, 2), nullable=True)
    communication_score: Mapped[Optional[Decimal]] = mapped_column(Numeric(5, 2), nullable=True)
    mistakes: Mapped[list[str]] = mapped_column(ARRAY(Text), nullable=False, server_default="{}")
    attempt_number: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    item_embeddings: Mapped[Optional[list[float]]] = mapped_column(ARRAY(Float), nullable=True)
    transcript_ref: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class StudentTopicMastery(Base):
    __tablename__ = "student_topic_mastery"
    __table_args__ = (UniqueConstraint("student_id", "topic_id", name="uq_student_topic_mastery"),)

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    student_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    topic_id: Mapped[str] = mapped_column(String(100), nullable=False)
    recognition_level: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    recognition_attempts: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    recognition_last_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    recognition_consecutive_passes: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default="0"
    )
    application_level: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    application_attempts: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    application_last_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    application_consecutive_passes: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default="0"
    )
    explanation_level: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    explanation_attempts: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    explanation_last_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    explanation_consecutive_passes: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default="0"
    )
    assessed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    next_review_at: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class StudentCoverageLedger(Base):
    __tablename__ = "student_coverage_ledger"
    __table_args__ = (
        UniqueConstraint("student_id", "topic_id", name="uq_student_coverage_topic"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    student_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    topic_id: Mapped[str] = mapped_column(String(100), nullable=False)
    pool: Mapped[str] = mapped_column(String(10), nullable=False, server_default="NEW")
    first_tested_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    last_tested_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    attempts: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    correct: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    never_return_to_new: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class StudentMemoryFact(Base):
    __tablename__ = "student_memory"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    student_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    fact_type: Mapped[str] = mapped_column(String(50), nullable=False)
    topic_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    fact: Mapped[str] = mapped_column(Text, nullable=False)
    confidence: Mapped[Decimal] = mapped_column(Numeric(5, 4), nullable=False, server_default="0")
    evidence_count: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    last_observed: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    resolved_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class StudentTarget(Base):
    __tablename__ = "student_target"
    __table_args__ = (UniqueConstraint("student_id", name="uq_student_target_student"),)

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    student_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    target_companies: Mapped[list[str]] = mapped_column(
        ARRAY(Text), nullable=False, server_default="{}"
    )
    target_tier: Mapped[str] = mapped_column(
        String(50), nullable=False, server_default="mass_recruiter"
    )
    target_readiness: Mapped[int] = mapped_column(Integer, nullable=False, server_default="85")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class StudentReadinessSnapshot(Base):
    __tablename__ = "student_readiness_snapshot"
    __table_args__ = (
        UniqueConstraint("student_id", "snapshot_date", name="uq_student_readiness_snapshot_day"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    student_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    snapshot_date: Mapped[date] = mapped_column(Date, nullable=False)
    overall: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    base: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    execution_multiplier: Mapped[Decimal] = mapped_column(
        Numeric(4, 2), nullable=False, server_default="1"
    )
    coverage: Mapped[Decimal] = mapped_column(Numeric(5, 4), nullable=False, server_default="0")
    measured_pillars: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    total_pillars: Mapped[int] = mapped_column(Integer, nullable=False, server_default="6")
    eta_days: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    pillars: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, server_default="{}")
    focus_pillar: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    weakest_pillar: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    gates: Mapped[list[Any]] = mapped_column(JSONB, nullable=False, server_default="[]")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class StudentMissionAnchor(Base):
    __tablename__ = "student_mission_anchor"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    student_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    plan_id: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    anchor_date: Mapped[date] = mapped_column(Date, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class StudentDailyTaskLedger(Base):
    __tablename__ = "student_daily_task_ledger"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    student_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    plan_id: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    local_date: Mapped[date] = mapped_column(Date, nullable=False)
    task_key: Mapped[str] = mapped_column(String(128), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False)
    source: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    score: Mapped[Optional[Decimal]] = mapped_column(Numeric(5, 2), nullable=True)
    text_hash: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    widget_spec: Mapped[Optional[dict[str, Any]]] = mapped_column(JSONB, nullable=True)
    why_this: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    skill_demand_score: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class StudentDailyActivity(Base):
    __tablename__ = "student_daily_activity"
    __table_args__ = (
        UniqueConstraint("student_id", "local_date", name="uq_student_daily_activity"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    student_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    local_date: Mapped[date] = mapped_column(Date, nullable=False)
    tasks_done: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    tasks_total: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    minutes: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    completion_rate_7d: Mapped[Optional[Decimal]] = mapped_column(Numeric(5, 4), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

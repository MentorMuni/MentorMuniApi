"""ORM models for student Week-1 roadmap and generated 90-day plans."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from sqlalchemy import BigInteger, DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.common.database.base import Base


class StudentRoadmapWeek(Base):
    __tablename__ = "student_roadmap_weeks"
    __table_args__ = (UniqueConstraint("user_id", "week_number", name="uq_student_roadmap_weeks_user_week"),)

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    week_number: Mapped[int] = mapped_column(Integer, nullable=False, default=1, server_default="1")
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="in_progress", server_default="in_progress")
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )
    progress_topics_json: Mapped[Optional[dict[str, Any]]] = mapped_column(JSONB, nullable=True)
    progress_topics_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    steps: Mapped[list[StudentRoadmapStep]] = relationship(
        "StudentRoadmapStep",
        back_populates="week",
        cascade="all, delete-orphan",
        order_by="StudentRoadmapStep.step_order",
    )


class StudentRoadmapStep(Base):
    __tablename__ = "student_roadmap_steps"
    __table_args__ = (UniqueConstraint("week_id", "tool_code", name="uq_student_roadmap_steps_week_tool"),)

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    week_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("student_roadmap_weeks.id", ondelete="CASCADE"), nullable=False, index=True
    )
    tool_code: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    step_order: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="locked", server_default="locked")
    score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    label: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    technical_score: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    communication_score: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    strengths_json: Mapped[list[Any]] = mapped_column(JSONB, nullable=False, server_default="[]")
    weaknesses_json: Mapped[list[Any]] = mapped_column(JSONB, nullable=False, server_default="[]")
    recommendations_json: Mapped[list[Any]] = mapped_column(JSONB, nullable=False, server_default="[]")
    latest_result_id: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    week: Mapped[StudentRoadmapWeek] = relationship("StudentRoadmapWeek", back_populates="steps")


class StudentAssessmentResult(Base):
    __tablename__ = "student_assessment_results"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    week_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("student_roadmap_weeks.id", ondelete="CASCADE"), nullable=False
    )
    step_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("student_roadmap_steps.id", ondelete="CASCADE"), nullable=False, index=True
    )
    tool_code: Mapped[str] = mapped_column(String(64), nullable=False)
    attempt_number: Mapped[int] = mapped_column(Integer, nullable=False, default=1, server_default="1")
    score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    label: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    technical_score: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    communication_score: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    strengths_json: Mapped[list[Any]] = mapped_column(JSONB, nullable=False, server_default="[]")
    weaknesses_json: Mapped[list[Any]] = mapped_column(JSONB, nullable=False, server_default="[]")
    recommendations_json: Mapped[list[Any]] = mapped_column(JSONB, nullable=False, server_default="[]")
    raw_json: Mapped[Optional[dict[str, Any]]] = mapped_column(JSONB, nullable=True)
    source: Mapped[str] = mapped_column(String(32), nullable=False, default="roadmap", server_default="roadmap")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class StudentGeneratedRoadmap(Base):
    __tablename__ = "student_generated_roadmaps"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    week_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("student_roadmap_weeks.id", ondelete="CASCADE"), nullable=False
    )
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="generating", server_default="generating")
    model: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    prompt_version: Mapped[str] = mapped_column(
        String(64), nullable=False, default="placement_90day_v1", server_default="placement_90day_v1"
    )
    input_snapshot_json: Mapped[Optional[dict[str, Any]]] = mapped_column(JSONB, nullable=True)
    plan_json: Mapped[Optional[dict[str, Any]]] = mapped_column(JSONB, nullable=True)
    summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

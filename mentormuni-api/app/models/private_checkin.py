from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING, Optional

from sqlalchemy import ForeignKey, Integer, String, Text, DateTime, JSON, Boolean, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.common.database.base import Base

if TYPE_CHECKING:
    from app.models.user import User


class PrivateStudentCheckIn(Base):
    """Parent record for a student's private check-in session.
    
    One check-in = one "Know Me" flow (placement pressure → technical → projects → etc).
    Separate table; never queried by TPO/HOD layer.
    """

    __tablename__ = "private_student_checkins"
    __table_args__ = (Index("ix_psc_student_id_created", "student_id", "created_at"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    student_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    organization_id: Mapped[int] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True
    )

    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc)
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    responses: Mapped[list[PrivateStudentResponse]] = relationship(
        "PrivateStudentResponse", back_populates="checkin", cascade="all, delete-orphan"
    )
    insights: Mapped[list[PrivateStudentInsight]] = relationship(
        "PrivateStudentInsight", back_populates="checkin", cascade="all, delete-orphan"
    )


class PrivateStudentResponse(Base):
    """Individual response to a question in a check-in.
    
    One row per question-answer pair; never visible to non-owner.
    """

    __tablename__ = "private_student_responses"
    __table_args__ = (Index("ix_psr_checkin_id", "checkin_id"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    checkin_id: Mapped[int] = mapped_column(
        ForeignKey("private_student_checkins.id", ondelete="CASCADE"), nullable=False, index=True
    )

    question_key: Mapped[str] = mapped_column(String(128), nullable=False)
    response_type: Mapped[str] = mapped_column(String(32), nullable=False)
    response_value: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))

    checkin: Mapped[PrivateStudentCheckIn] = relationship(
        "PrivateStudentCheckIn", back_populates="responses"
    )


class PrivateStudentInsight(Base):
    """AI-generated insight from a completed check-in.
    
    Stored once per check-in to avoid re-generating. Private to student.
    """

    __tablename__ = "private_student_insights"
    __table_args__ = (Index("ix_psi_student_id_created", "student_id", "created_at"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    student_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    checkin_id: Mapped[int] = mapped_column(
        ForeignKey("private_student_checkins.id", ondelete="CASCADE"), nullable=False
    )

    source: Mapped[str] = mapped_column(String(32), default="openai")
    model: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)

    headline: Mapped[str] = mapped_column(Text, nullable=False)
    what_i_hear: Mapped[list[str]] = mapped_column(JSON, default=list)
    blockers: Mapped[list[dict]] = mapped_column(JSON, default=list)
    action_plan: Mapped[list[dict]] = mapped_column(JSON, default=list)
    full_insight_json: Mapped[dict] = mapped_column(JSON, default=dict)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))

    checkin: Mapped[PrivateStudentCheckIn] = relationship(
        "PrivateStudentCheckIn", back_populates="insights"
    )


class PrivateStudentProgress(Base):
    """Optional: Track confidence/metrics over time for 30–45 day check-ins.
    
    Stores snapshots of self-reported confidence metrics.
    """

    __tablename__ = "private_student_progress"
    __table_args__ = (Index("ix_psp_student_id_created", "student_id", "created_at"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    student_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    checkin_id: Mapped[int] = mapped_column(
        ForeignKey("private_student_checkins.id", ondelete="CASCADE"), nullable=False
    )

    metric_key: Mapped[str] = mapped_column(String(64), nullable=False)
    value_before: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    value_after: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))

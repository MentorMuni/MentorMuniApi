"""Student White Board — private sticky notes + one morning mentorship per day."""

from __future__ import annotations

from datetime import date, datetime
from typing import Any, Optional

from sqlalchemy import (
    BigInteger,
    Date,
    DateTime,
    Float,
    ForeignKey,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.common.database.base import Base


NOTE_STATUS_OPEN = "OPEN"
NOTE_STATUS_RESOLVED = "RESOLVED"

MENTORSHIP_GENERATING = "GENERATING"
MENTORSHIP_READY = "READY"


class WhiteboardNote(Base):
    __tablename__ = "whiteboard_notes"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    student_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    organization_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    body: Mapped[str] = mapped_column(Text, nullable=False)
    color: Mapped[str] = mapped_column(String(16), nullable=False, default="canary")
    status: Mapped[str] = mapped_column(String(16), nullable=False, default=NOTE_STATUS_OPEN, index=True)
    board_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    pin_x: Mapped[float] = mapped_column(Float, nullable=False, default=8.0)
    pin_y: Mapped[float] = mapped_column(Float, nullable=False, default=8.0)
    rotation: Mapped[float] = mapped_column(Float, nullable=False, default=-3.0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
    resolved_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)


class WhiteboardMentorship(Base):
    __tablename__ = "whiteboard_mentorships"
    __table_args__ = (
        UniqueConstraint("student_id", "mentorship_date", name="uq_whiteboard_mentorship_student_date"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    student_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    organization_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    mentorship_date: Mapped[date] = mapped_column(Date, nullable=False)
    source_notes_date: Mapped[date] = mapped_column(Date, nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default=MENTORSHIP_GENERATING, index=True)
    headline: Mapped[str] = mapped_column(Text, nullable=False, default="")
    greeting: Mapped[str] = mapped_column(Text, nullable=False, default="")
    what_changed: Mapped[str] = mapped_column(Text, nullable=False, default="")
    diagnosis: Mapped[str] = mapped_column(Text, nullable=False, default="")
    actions_json: Mapped[list[Any]] = mapped_column(JSONB, nullable=False, server_default="[]")
    callout: Mapped[str] = mapped_column(Text, nullable=False, default="")
    closing: Mapped[str] = mapped_column(Text, nullable=False, default="")
    source: Mapped[str] = mapped_column(String(16), nullable=False, default="openai")
    model: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    raw_json: Mapped[Optional[dict[str, Any]]] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

"""Platform Help Center tickets — reporter identity is never exposed to platform UI."""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import JSON, BigInteger, DateTime, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.common.database.base import Base


class PlatformSupportTicket(Base):
    __tablename__ = "platform_support_tickets"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    organization_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    organization_name: Mapped[str] = mapped_column(String(255), nullable=False)
    organization_code: Mapped[str] = mapped_column(String(64), nullable=False)
    source_portal: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    reporter_user_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    reporter_role_code: Mapped[str] = mapped_column(String(32), nullable=False)
    category: Mapped[str] = mapped_column(String(32), nullable=False, default="other")
    subject: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="OPEN", index=True)
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
    closed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    closed_by_kind: Mapped[Optional[str]] = mapped_column(String(16), nullable=True)

    replies: Mapped[list["PlatformSupportReply"]] = relationship(
        back_populates="ticket",
        cascade="all, delete-orphan",
        order_by="PlatformSupportReply.created_at",
    )


class PlatformSupportReply(Base):
    __tablename__ = "platform_support_replies"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    ticket_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("platform_support_tickets.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    author_kind: Mapped[str] = mapped_column(String(16), nullable=False)
    author_user_id: Mapped[Optional[int]] = mapped_column(
        BigInteger,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    author_platform_user_id: Mapped[Optional[int]] = mapped_column(
        BigInteger,
        ForeignKey("platform_users.id", ondelete="SET NULL"),
        nullable=True,
    )
    body: Mapped[str] = mapped_column(Text, nullable=False)
    attachments_json: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    ticket: Mapped[PlatformSupportTicket] = relationship(back_populates="replies")

"""ORM for cached company hiring intelligence."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from sqlalchemy import BigInteger, DateTime, Float, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.common.database.base import Base


class CompanyIntelligence(Base):
    __tablename__ = "company_intelligence"
    __table_args__ = (
        UniqueConstraint(
            "company_key",
            "role_key",
            "country_key",
            name="uq_company_intelligence_keys",
        ),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    slug: Mapped[str] = mapped_column(String(220), nullable=False, unique=True, index=True)

    company_name: Mapped[str] = mapped_column(String(160), nullable=False)
    role_name: Mapped[str] = mapped_column(String(160), nullable=False)
    country: Mapped[str] = mapped_column(String(80), nullable=False)

    company_key: Mapped[str] = mapped_column(String(160), nullable=False, index=True)
    role_key: Mapped[str] = mapped_column(String(160), nullable=False)
    country_key: Mapped[str] = mapped_column(String(80), nullable=False)

    status: Mapped[str] = mapped_column(String(32), nullable=False, server_default="generating")
    overall_confidence: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    evidence_strength: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    last_updated_estimate: Mapped[Optional[str]] = mapped_column(String(8), nullable=True)

    payload_json: Mapped[Optional[dict[str, Any]]] = mapped_column(JSONB, nullable=True)
    prompt_version: Mapped[str] = mapped_column(String(64), nullable=False, server_default="company_intelligence_v1")
    model: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

"""
organization_features — per-tenant feature toggles.

Uses feature_id → feature_catalog (no hardcoded feature_code strings in rows).
"""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Any, Optional

from sqlalchemy import BigInteger, Boolean, DateTime, ForeignKey, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.common.database.base import Base

if TYPE_CHECKING:
    from app.models.feature_catalog import FeatureCatalog
    from app.models.organization import Organization


class OrganizationFeature(Base):
    __tablename__ = "organization_features"
    __table_args__ = (
        UniqueConstraint(
            "organization_id",
            "feature_id",
            name="uq_org_features_org_feature",
        ),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)

    organization_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    feature_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("feature_catalog.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )

    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    configuration_json: Mapped[Optional[dict[str, Any]]] = mapped_column(JSONB, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    organization: Mapped["Organization"] = relationship(back_populates="features")
    feature: Mapped["FeatureCatalog"] = relationship(back_populates="organization_features")

    def __repr__(self) -> str:
        return (
            f"<OrganizationFeature id={self.id} "
            f"org={self.organization_id} feature={self.feature_id} enabled={self.enabled}>"
        )

"""
feature_catalog — master list of platform capabilities.

Rarely changes. organization_features references feature_id (not free-form strings).
"""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import BigInteger, DateTime, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.common.database.base import Base
from app.models.enums import FeatureCatalogStatus

if TYPE_CHECKING:
    from app.models.organization_feature import OrganizationFeature


class FeatureCatalog(Base):
    __tablename__ = "feature_catalog"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)

    feature_code: Mapped[str] = mapped_column(String(64), nullable=False, unique=True, index=True)
    feature_name: Mapped[str] = mapped_column(String(128), nullable=False)
    category: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default=FeatureCatalogStatus.ACTIVE.value,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    organization_features: Mapped[list["OrganizationFeature"]] = relationship(
        back_populates="feature",
    )

    def __repr__(self) -> str:
        return f"<FeatureCatalog id={self.id} code={self.feature_code!r}>"

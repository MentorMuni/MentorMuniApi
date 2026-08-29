"""
Table 1: organizations  (the Tenant)

Every college is one row. B2C students all belong to the single
"MentorMuni Public" organization (organization_type = PUBLIC).
"""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import BigInteger, DateTime, LargeBinary, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.common.database.base import Base
from app.models.enums import OrganizationStatus, OrganizationType

if TYPE_CHECKING:
    from app.models.department import Department
    from app.models.organization_feature import OrganizationFeature
    from app.models.organization_subscription import OrganizationSubscription
    from app.models.user import User


class Organization(Base):
    __tablename__ = "organizations"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    # Short unique code, e.g. "IIST" or "PUBLIC"
    code: Mapped[str] = mapped_column(String(64), nullable=False, unique=True, index=True)
    # DNS-safe subdomain for college portals, e.g. "medicaps" → medicaps.mentormuni.com
    # NULL for PUBLIC (individuals use apex).
    portal_slug: Mapped[Optional[str]] = mapped_column(String(64), nullable=True, index=True)

    organization_type: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default=OrganizationType.COLLEGE.value,
    )
    status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default=OrganizationStatus.ACTIVE.value,
    )

    contact_person: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    contact_email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    contact_phone: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)

    address: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    city: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    state: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    country: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)

    # College crest / logo (small image in Postgres — no external object store required)
    # deferred: list/detail JSON never pulls the blob unless an endpoint reads it.
    logo_bytes: Mapped[Optional[bytes]] = mapped_column(
        LargeBinary, nullable=True, deferred=True
    )
    logo_content_type: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    logo_updated_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

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

    # --- Relationships (Organization is the hub) ---
    # lazy="select" = load only when accessed (avoid pulling entire tenant graphs).
    subscriptions: Mapped[list["OrganizationSubscription"]] = relationship(
        back_populates="organization",
    )
    features: Mapped[list["OrganizationFeature"]] = relationship(
        back_populates="organization",
    )
    departments: Mapped[list["Department"]] = relationship(
        back_populates="organization",
    )
    users: Mapped[list["User"]] = relationship(
        back_populates="organization",
    )

    def __repr__(self) -> str:
        return f"<Organization id={self.id} code={self.code!r} type={self.organization_type}>"

"""
Table 5: departments

Only COLLEGE organizations create departments (CSE, IT, ECE, …).
PUBLIC (B2C) organizations do not.
"""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, DateTime, ForeignKey, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.common.database.base import Base
from app.models.enums import DepartmentStatus

if TYPE_CHECKING:
    from app.models.organization import Organization
    from app.models.user import User


class Department(Base):
    __tablename__ = "departments"
    __table_args__ = (
        # Same code can exist in different colleges, but not twice in one college.
        UniqueConstraint("organization_id", "code", name="uq_departments_org_code"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)

    organization_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    name: Mapped[str] = mapped_column(String(128), nullable=False)
    code: Mapped[str] = mapped_column(String(64), nullable=False)

    status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default=DepartmentStatus.ACTIVE.value,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    organization: Mapped["Organization"] = relationship(back_populates="departments")
    users: Mapped[list["User"]] = relationship(back_populates="department")

    def __repr__(self) -> str:
        return f"<Department id={self.id} code={self.code!r} org={self.organization_id}>"

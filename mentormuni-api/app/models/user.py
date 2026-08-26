"""
Table 6: users  (most important table)

One table for everyone:
  TPO (ORG_ADMIN)              → org=college,  department=NULL
  HOD (DEPARTMENT_ADMIN)       → org=college,  department=REQUIRED
  College Student (STUDENT)    → org=college,  department=REQUIRED
  Individual Student (STUDENT) → org=PUBLIC,   department=NULL

Backend service layer MUST enforce the department rules above
before insert/update. Status flow: PENDING → ACTIVE / REJECTED.
"""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import BigInteger, Boolean, DateTime, ForeignKey, Integer, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.common.database.base import Base
from app.models.enums import UserStatus

if TYPE_CHECKING:
    from app.models.department import Department
    from app.models.organization import Organization
    from app.models.role import Role


class User(Base):
    __tablename__ = "users"
    __table_args__ = (
        # Email and username unique within a tenant (multi-tenant safe).
        UniqueConstraint("organization_id", "email", name="uq_users_org_email"),
        UniqueConstraint("organization_id", "username", name="uq_users_org_username"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)

    organization_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    # NULL for ORG_ADMIN and Individual (PUBLIC) students.
    department_id: Mapped[Optional[int]] = mapped_column(
        BigInteger,
        ForeignKey("departments.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    role_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("roles.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )

    first_name: Mapped[str] = mapped_column(String(128), nullable=False)
    last_name: Mapped[str] = mapped_column(String(128), nullable=False)
    email: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    mobile: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    username: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    # ORG_ADMIN only: TPO | DEAN | DIRECTOR. NULL for HOD / students.
    org_admin_title: Mapped[Optional[str]] = mapped_column(String(32), nullable=True, index=True)
    # DEPARTMENT_ADMIN only: HOD | PLACEMENT_COORDINATOR. NULL treated as HOD.
    dept_admin_title: Mapped[Optional[str]] = mapped_column(String(32), nullable=True, index=True)

    # bcrypt hash — never store plain text. Use app.common.security.passwords.
    # NULL while status=INVITED (TPO has not set password yet).
    password_hash: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default=UserStatus.PENDING.value,
        index=True,
    )
    must_change_password: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default="false",
    )

    # One-time activation for TPO invite (hashed token; raw token only emailed once).
    activation_token_hash: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    activation_expires_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # Forgot-password flow (hashed token; raw token only emailed once).
    password_reset_token_hash: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    password_reset_expires_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # College enrollment metadata (optional until import/manual/register fills them).
    roll_number: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    batch_year: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    # Individual (PUBLIC) students: free-text college profile (not a tenant org).
    college_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    course_or_branch: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)

    deleted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Who approved this user (HOD approving a college student).
    approved_by: Mapped[Optional[int]] = mapped_column(
        BigInteger,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    approved_at: Mapped[Optional[datetime]] = mapped_column(
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

    organization: Mapped["Organization"] = relationship(back_populates="users")
    department: Mapped[Optional["Department"]] = relationship(back_populates="users")
    role: Mapped["Role"] = relationship(back_populates="users")
    approver: Mapped[Optional["User"]] = relationship(
        remote_side="User.id",
        foreign_keys=[approved_by],
    )

    def __repr__(self) -> str:
        return (
            f"<User id={self.id} username={self.username!r} "
            f"status={self.status} org={self.organization_id}>"
        )

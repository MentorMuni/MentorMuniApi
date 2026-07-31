"""
Table 4: roles

Initial rows (seeded by Alembic):
  ORG_ADMIN          → TPO
  DEPARTMENT_ADMIN   → HOD
  STUDENT            → College or Individual student

RULE: Always look up by role_code. Never hardcode role IDs.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.common.database.base import Base

if TYPE_CHECKING:
    from app.models.role_permission import RolePermission
    from app.models.user import User


class Role(Base):
    __tablename__ = "roles"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)

    role_code: Mapped[str] = mapped_column(String(64), nullable=False, unique=True, index=True)
    role_name: Mapped[str] = mapped_column(String(128), nullable=False)

    users: Mapped[list["User"]] = relationship(back_populates="role")
    permission_links: Mapped[list["RolePermission"]] = relationship(back_populates="role")

    def __repr__(self) -> str:
        return f"<Role id={self.id} code={self.role_code!r}>"

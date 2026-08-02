"""
platform_users — MentorMuni employees (Platform Admin portal only).

Separate from tenant `users` table. Never mixed with TPO / HOD / Student.
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import BigInteger, Boolean, DateTime, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.common.database.base import Base
from app.models.enums import PlatformRole, PlatformUserStatus


class PlatformUser(Base):
    __tablename__ = "platform_users"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[str] = mapped_column(String(255), nullable=False, unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)

    role: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default=PlatformRole.PLATFORM_ADMIN.value,
    )
    status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default=PlatformUserStatus.ACTIVE.value,
    )
    must_change_password: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default="false",
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    def __repr__(self) -> str:
        return f"<PlatformUser id={self.id} email={self.email!r} role={self.role}>"

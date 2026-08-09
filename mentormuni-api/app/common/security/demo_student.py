"""Dev-only: map frontend demo/local fake JWTs to a real STUDENT user."""

from __future__ import annotations

import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.common.security.passwords import hash_password
from app.core.config import settings
from app.models.enums import RoleCode, UserStatus
from app.models.organization import Organization
from app.models.role import Role
from app.models.user import User

logger = logging.getLogger("auth.demo_student")

DEMO_CODING_EMAIL = "coding-demo@mentormuni.local"
DEMO_CODING_USERNAME = "coding_demo"


def is_dev_demo_bearer(token: str) -> bool:
    """Frontend demo/local sessions use fake tokens like demo.student.<ts>."""
    if (settings.app_env or "").lower() not in {"development", "dev", "local", "test"}:
        return False
    t = (token or "").strip()
    return t.startswith("demo.student.") or t.startswith("local.student.")


async def resolve_dev_demo_student(db: AsyncSession) -> User | None:
    """
    Ensure an ACTIVE PUBLIC-org student exists for local Coding Round smoke tests.
    Only used when APP_ENV is development-like.
    """
    existing = (
        await db.execute(
            select(User)
            .where(User.email == DEMO_CODING_EMAIL, User.deleted_at.is_(None))
            .options(
                selectinload(User.role),
                selectinload(User.organization),
                selectinload(User.department),
            )
        )
    ).scalar_one_or_none()
    if existing is not None:
        if existing.status != UserStatus.ACTIVE.value:
            existing.status = UserStatus.ACTIVE.value
            await db.flush()
        return existing

    role = (
        await db.execute(select(Role).where(Role.role_code == RoleCode.STUDENT.value))
    ).scalar_one_or_none()
    if role is None:
        logger.error("STUDENT role missing — cannot create coding demo user")
        return None

    org = (
        await db.execute(
            select(Organization).where(Organization.code == "PUBLIC")
        )
    ).scalar_one_or_none()
    if org is None:
        # Fallback: any active org
        org = (
            await db.execute(
                select(Organization)
                .where(Organization.status == "ACTIVE")
                .order_by(Organization.id.asc())
                .limit(1)
            )
        ).scalar_one_or_none()
    if org is None:
        logger.error("No organization available for coding demo user")
        return None

    user = User(
        organization_id=org.id,
        department_id=None,
        role_id=role.id,
        first_name="Coding",
        last_name="Demo",
        email=DEMO_CODING_EMAIL,
        username=DEMO_CODING_USERNAME,
        password_hash=hash_password("Demo@123"),
        status=UserStatus.ACTIVE.value,
    )
    db.add(user)
    await db.flush()
    # Reload with relationships
    user = (
        await db.execute(
            select(User)
            .where(User.id == user.id)
            .options(
                selectinload(User.role),
                selectinload(User.organization),
                selectinload(User.department),
            )
        )
    ).scalar_one()
    logger.info("Created coding demo student id=%s org=%s", user.id, org.code)
    return user

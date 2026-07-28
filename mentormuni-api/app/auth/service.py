"""Auth service: login, me, change-password."""

from __future__ import annotations

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.common.security.passwords import hash_password, verify_password
from app.core.config import settings
from app.models.enums import UserStatus
from app.models.organization import Organization
from app.models.user import User


class AuthError(Exception):
    def __init__(self, message: str, *, status_code: int = 400) -> None:
        super().__init__(message)
        self.message = message
        self.status_code = status_code


async def authenticate_user(
    db: AsyncSession,
    *,
    password: str,
    email: str | None = None,
    username: str | None = None,
    organization_code: str | None = None,
) -> User:
    if not email and not username:
        raise AuthError("Provide email or username.", status_code=422)

    stmt = (
        select(User)
        .join(Organization, User.organization_id == Organization.id)
        .options(
            selectinload(User.role),
            selectinload(User.organization),
            selectinload(User.department),
        )
    )

    if organization_code:
        stmt = stmt.where(Organization.code == organization_code.upper())

    if email and username:
        stmt = stmt.where(or_(User.email == email.lower(), User.username == username))
    elif email:
        stmt = stmt.where(User.email == email.lower())
    else:
        stmt = stmt.where(User.username == username)

    result = await db.execute(stmt)
    users = list(result.scalars().unique().all())

    if not users:
        raise AuthError("Invalid credentials.", status_code=401)
    if len(users) > 1:
        raise AuthError(
            "Multiple accounts match. Pass organization_code to disambiguate.",
            status_code=400,
        )

    user = users[0]
    if not user.password_hash or not verify_password(password, user.password_hash):
        raise AuthError("Invalid credentials.", status_code=401)
    if user.status == UserStatus.INVITED.value:
        raise AuthError(
            "Account invited but not activated. Set your password via the activation link.",
            status_code=403,
        )
    if user.status == UserStatus.PENDING.value:
        raise AuthError("Account pending approval.", status_code=403)
    if user.status == UserStatus.REJECTED.value:
        raise AuthError("Account was rejected.", status_code=403)
    if user.status == UserStatus.BLOCKED.value:
        raise AuthError("Account is blocked.", status_code=403)
    if user.status != UserStatus.ACTIVE.value:
        raise AuthError(f"Account is {user.status}.", status_code=403)
    return user


async def change_password(
    db: AsyncSession,
    *,
    user: User,
    current_password: str,
    new_password: str,
) -> None:
    if not user.password_hash or not verify_password(current_password, user.password_hash):
        raise AuthError("Current password is incorrect.", status_code=400)
    user.password_hash = hash_password(new_password)
    await db.flush()


def token_expires_minutes() -> int:
    return settings.jwt_expire_minutes

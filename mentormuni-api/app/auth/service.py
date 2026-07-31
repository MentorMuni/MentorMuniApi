"""Auth service: login, me, change-password, forgot/reset password."""

from __future__ import annotations

import hashlib
import logging
import secrets
from datetime import datetime, timedelta, timezone

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.common.email.exceptions import EmailError
from app.common.email.flows import send_password_reset_email
from app.common.organization_access import (
    OrganizationAccessError,
    ensure_organization_active_for_login,
)
from app.common.security.passwords import hash_password, verify_password
from app.common.tenant.deps import load_permissions_for_role
from app.core.config import settings
from app.models.enums import UserStatus
from app.models.organization import Organization
from app.models.user import User

logger = logging.getLogger(__name__)


class AuthError(Exception):
    def __init__(self, message: str, *, status_code: int = 400) -> None:
        super().__init__(message)
        self.message = message
        self.status_code = status_code


def _hash_token(raw: str) -> str:
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


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
        .where(User.deleted_at.is_(None))
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

    try:
        role_code = user.role.role_code if user.role else None
        ensure_organization_active_for_login(user.organization, role_code=role_code)
    except OrganizationAccessError as exc:
        raise AuthError(exc.message, status_code=exc.status_code) from exc

    return user


async def permissions_for_user(db: AsyncSession, user: User) -> list[str]:
    perms = await load_permissions_for_role(db, user.role_id)
    return sorted(perms)


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


async def request_password_reset(
    db: AsyncSession,
    *,
    email: str,
    organization_code: str | None = None,
) -> tuple[str, bool]:
    """
    Always returns a generic success message to the caller.
    If a matching ACTIVE user exists, emails a reset link.
    """
    generic = "If an account exists for that email, a reset link has been sent."
    stmt = (
        select(User)
        .join(Organization, User.organization_id == Organization.id)
        .where(User.email == email.lower().strip())
        .where(User.deleted_at.is_(None))
        .options(selectinload(User.organization), selectinload(User.role))
    )
    if organization_code:
        stmt = stmt.where(Organization.code == organization_code.upper())

    result = await db.execute(stmt)
    users = list(result.scalars().unique().all())
    if len(users) != 1:
        return generic, False

    user = users[0]
    if user.status != UserStatus.ACTIVE.value or not user.password_hash:
        return generic, False

    raw_token = secrets.token_urlsafe(32)
    user.password_reset_token_hash = _hash_token(raw_token)
    user.password_reset_expires_at = datetime.now(timezone.utc) + timedelta(hours=2)
    await db.flush()

    try:
        await send_password_reset_email(
            to_email=user.email,
            first_name=user.first_name,
            last_name=user.last_name,
            organization_name=user.organization.name,
            raw_token=raw_token,
            expires_at=user.password_reset_expires_at,
        )
        return generic, True
    except EmailError as exc:
        logger.warning("password_reset_email_failed to=%s err=%s", user.email, exc)
        return generic, False


async def reset_password(db: AsyncSession, *, token: str, new_password: str) -> None:
    token_hash = _hash_token(token)
    result = await db.execute(
        select(User)
        .where(User.password_reset_token_hash == token_hash)
        .where(User.deleted_at.is_(None))
        .options(selectinload(User.organization), selectinload(User.role))
    )
    user = result.scalar_one_or_none()
    if user is None:
        raise AuthError("Invalid or expired reset token.", status_code=400)
    if user.password_reset_expires_at and user.password_reset_expires_at < datetime.now(
        timezone.utc
    ):
        raise AuthError("Reset token has expired.", status_code=400)
    if user.status != UserStatus.ACTIVE.value:
        raise AuthError("Account cannot reset password in its current status.", status_code=403)

    try:
        role_code = user.role.role_code if user.role else None
        ensure_organization_active_for_login(user.organization, role_code=role_code)
    except OrganizationAccessError as exc:
        raise AuthError(exc.message, status_code=exc.status_code) from exc

    user.password_hash = hash_password(new_password)
    user.password_reset_token_hash = None
    user.password_reset_expires_at = None
    await db.flush()


async def activate_invited_user(
    db: AsyncSession,
    *,
    token: str,
    new_password: str,
) -> User:
    """Activate INVITED TPO or HOD (shared org-portal activate flow)."""
    from app.common.organization_access import ensure_organization_accepts_activation

    token_hash = _hash_token(token)
    result = await db.execute(
        select(User)
        .where(User.activation_token_hash == token_hash)
        .where(User.deleted_at.is_(None))
        .options(selectinload(User.role), selectinload(User.organization))
    )
    user = result.scalar_one_or_none()
    if user is None:
        raise AuthError("Invalid or already-used activation token.", status_code=400)
    if user.status != UserStatus.INVITED.value:
        raise AuthError("Account is not awaiting activation.", status_code=400)
    if user.activation_expires_at and user.activation_expires_at < datetime.now(timezone.utc):
        raise AuthError("Activation token expired. Ask admin to re-invite.", status_code=400)

    if user.organization is not None:
        try:
            ensure_organization_accepts_activation(user.organization)
        except OrganizationAccessError as exc:
            raise AuthError(exc.message, status_code=exc.status_code) from exc

    user.password_hash = hash_password(new_password)
    user.status = UserStatus.ACTIVE.value
    user.activation_token_hash = None
    user.activation_expires_at = None
    await db.flush()
    return user


async def audit_hod_activate(db: AsyncSession, user: User) -> None:
    from app.common.audit import write_audit

    await write_audit(
        db,
        organization_id=user.organization_id,
        actor_user_id=user.id,
        action="hod.activate",
        entity_type="user",
        entity_id=user.id,
        payload={"department_id": user.department_id},
    )


def token_expires_minutes() -> int:
    return settings.jwt_expire_minutes

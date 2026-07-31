"""
Shared FastAPI dependencies for Phase 1 routes.

Usage:
  - require_api_key          → every Phase 1 route
  - get_current_user         → logged-in user (Bearer JWT)
  - get_current_active_user  → logged-in + status ACTIVE
"""

from __future__ import annotations

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.common.database.session import get_db
from app.common.organization_access import (
    OrganizationAccessError,
    ensure_organization_active_for_login,
)
from app.common.security.api_key import require_api_key
from app.common.security.jwt import decode_access_token
from app.models.enums import UserStatus
from app.models.user import User

_bearer = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
    db: AsyncSession = Depends(get_db),
) -> User:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing Authorization Bearer token.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    payload = decode_access_token(credentials.credentials, expected_scope="tenant")
    try:
        user_id = int(payload["sub"])
    except (KeyError, TypeError, ValueError) as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token subject.",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc

    result = await db.execute(
        select(User)
        .where(User.id == user_id)
        .where(User.deleted_at.is_(None))
        .options(
            selectinload(User.role),
            selectinload(User.organization),
            selectinload(User.department),
        )
    )
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user


async def get_current_active_user(
    user: User = Depends(get_current_user),
) -> User:
    if user.status != UserStatus.ACTIVE.value:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Account is {user.status}. Only ACTIVE users can access this.",
        )
    # JWT issued before suspend → still locked out on the next authenticated call.
    try:
        role_code = user.role.role_code if user.role else None
        if user.organization is not None:
            ensure_organization_active_for_login(user.organization, role_code=role_code)
    except OrganizationAccessError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc
    return user


def require_roles(*role_codes: str):
    """Dependency factory: allow only the given role_code values."""

    async def _checker(user: User = Depends(get_current_active_user)) -> User:
        code = user.role.role_code if user.role else None
        if code not in role_codes:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Requires one of roles: {', '.join(role_codes)}",
            )
        return user

    return _checker


# Re-export so routers can import deps from one place.
__all__ = [
    "get_current_active_user",
    "get_current_user",
    "get_db",
    "require_api_key",
    "require_roles",
]

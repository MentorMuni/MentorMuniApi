"""Platform portal dependencies — requires platform JWT scope."""

from __future__ import annotations

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.database.session import get_db
from app.common.security.api_key import require_api_key
from app.common.security.jwt import decode_access_token
from app.models.enums import PlatformUserStatus
from app.models.platform_user import PlatformUser

_bearer = HTTPBearer(auto_error=False)


async def get_current_platform_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
    db: AsyncSession = Depends(get_db),
) -> PlatformUser:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing Authorization Bearer token.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    payload = decode_access_token(credentials.credentials, expected_scope="platform")
    try:
        user_id = int(payload["sub"])
    except (KeyError, TypeError, ValueError) as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token subject.",
        ) from exc

    user = await db.get(PlatformUser, user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Platform user not found.")
    if user.status != PlatformUserStatus.ACTIVE.value:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Platform user is inactive.")
    return user


def require_platform_roles(*roles: str):
    async def _checker(user: PlatformUser = Depends(get_current_platform_user)) -> PlatformUser:
        if user.role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Requires one of: {', '.join(roles)}",
            )
        return user

    return _checker


__all__ = [
    "get_current_platform_user",
    "get_db",
    "require_api_key",
    "require_platform_roles",
]

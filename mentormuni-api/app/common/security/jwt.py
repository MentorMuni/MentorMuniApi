"""
JWT access tokens for logged-in users.

Frontend flow:
  1. Every request → header X-API-Key: <platform key>
  2. After login   → header Authorization: Bearer <access_token>
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

import jwt

from app.common.security.auth_errors import (
    TOKEN_EXPIRED,
    TOKEN_INVALID,
    TOKEN_WRONG_SCOPE,
    TOKEN_WRONG_TYPE,
    raise_unauthorized,
)
from app.core.config import settings


def create_access_token(
    *,
    user_id: int,
    scope: str = "tenant",
    extra: dict[str, Any] | None = None,
) -> str:
    """
    scope:
      - "tenant"   → college/public portal users (TPO/HOD/Student)
      - "platform" → MentorMuni Platform Admin portal employees
    """
    now = datetime.now(timezone.utc)
    payload: dict[str, Any] = {
        "sub": str(user_id),
        "iat": now,
        "exp": now + timedelta(minutes=settings.jwt_expire_minutes),
        "type": "access",
        "scope": scope,
    }
    if extra:
        payload.update(extra)
    return jwt.encode(
        payload,
        settings.effective_jwt_secret,
        algorithm=settings.jwt_algorithm,
    )


def decode_access_token(token: str, *, expected_scope: str | None = None) -> dict[str, Any]:
    try:
        payload = jwt.decode(
            token,
            settings.effective_jwt_secret,
            algorithms=[settings.jwt_algorithm],
        )
    except jwt.ExpiredSignatureError:
        raise_unauthorized(
            code=TOKEN_EXPIRED,
            message="Token expired. Please log in again.",
        )
    except jwt.InvalidTokenError:
        raise_unauthorized(code=TOKEN_INVALID, message="Invalid token.")

    if payload.get("type") != "access":
        raise_unauthorized(code=TOKEN_WRONG_TYPE, message="Invalid token type.")
    if expected_scope and payload.get("scope", "tenant") != expected_scope:
        raise_unauthorized(
            code=TOKEN_WRONG_SCOPE,
            message=f"Token scope must be '{expected_scope}'.",
        )
    return payload

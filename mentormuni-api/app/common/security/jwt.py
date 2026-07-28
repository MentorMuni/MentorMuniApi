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
from fastapi import HTTPException, status

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
    except jwt.ExpiredSignatureError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token expired. Please log in again.",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc
    except jwt.InvalidTokenError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token.",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc

    if payload.get("type") != "access":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token type.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if expected_scope and payload.get("scope", "tenant") != expected_scope:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Token scope must be '{expected_scope}'.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return payload

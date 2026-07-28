"""
Platform API-key authentication.

How it works (simple + hard to crack):
1. Backend stores a long random secret in env: API_KEY
2. Frontend sends the same value on every request: header `X-API-Key`
3. We compare with secrets.compare_digest (constant-time → resists timing attacks)

Generate a key:
    python -c "import secrets; print(secrets.token_urlsafe(48))"

Put the same value in:
  - Backend:  API_KEY=...
  - Frontend: VITE_API_KEY / NEXT_PUBLIC_API_KEY / etc.
"""

from __future__ import annotations

import secrets

from fastapi import Header, HTTPException, status

from app.core.config import settings

API_KEY_HEADER = "X-API-Key"


def verify_api_key(provided: str | None) -> bool:
    """Constant-time compare. Returns False if either side is missing."""
    expected = settings.api_key
    if not expected or not provided:
        return False
    return secrets.compare_digest(provided, expected)


async def require_api_key(
    x_api_key: str | None = Header(default=None, alias=API_KEY_HEADER),
) -> None:
    """
    FastAPI dependency. Attach to routers that must be locked down:

        router = APIRouter(dependencies=[Depends(require_api_key)])

    Or per-route:

        @router.get("/me", dependencies=[Depends(require_api_key)])
    """
    if not settings.is_api_key_configured:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="API_KEY is not configured on the server.",
        )
    if not verify_api_key(x_api_key):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API key.",
            headers={"WWW-Authenticate": "ApiKey"},
        )

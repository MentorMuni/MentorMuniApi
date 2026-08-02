"""Stable auth error payloads for FE (401 auto-logout, 403 permission).

FastAPI ``detail`` is either a string (legacy) or:

```json
{"code": "TOKEN_EXPIRED", "message": "Token expired. Please log in again."}
```

FE should prefer ``detail.message`` when ``detail`` is an object, and treat
these ``code`` values as the contract (not free-text matching alone).
"""

from __future__ import annotations

from typing import Any, NoReturn

from fastapi import HTTPException, status


# ----- Codes (stable; do not rename lightly) -----

INVALID_API_KEY = "INVALID_API_KEY"
API_KEY_NOT_CONFIGURED = "API_KEY_NOT_CONFIGURED"

TOKEN_MISSING = "TOKEN_MISSING"
TOKEN_EXPIRED = "TOKEN_EXPIRED"
TOKEN_INVALID = "TOKEN_INVALID"
TOKEN_WRONG_SCOPE = "TOKEN_WRONG_SCOPE"
TOKEN_WRONG_TYPE = "TOKEN_WRONG_TYPE"

ACCOUNT_INACTIVE = "ACCOUNT_INACTIVE"
FORBIDDEN_ROLE = "FORBIDDEN_ROLE"
INVALID_CREDENTIALS = "INVALID_CREDENTIALS"


def auth_detail(*, code: str, message: str) -> dict[str, str]:
    return {"code": code, "message": message}


def raise_unauthorized(
    *,
    code: str,
    message: str,
    www_authenticate: bool = True,
) -> NoReturn:
    headers: dict[str, Any] | None = None
    if www_authenticate:
        headers = {"WWW-Authenticate": "Bearer"}
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=auth_detail(code=code, message=message),
        headers=headers,
    )


def raise_forbidden(*, code: str, message: str) -> NoReturn:
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail=auth_detail(code=code, message=message),
    )

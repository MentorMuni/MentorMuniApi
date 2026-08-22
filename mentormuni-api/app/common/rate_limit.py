"""Shared SlowAPI limiter instance for app + routers.

Default API budget: 100 requests/minute per client key.

Keying strategy (campus-safe):
- Prefer Authorization Bearer token fingerprint so 500–1000 students behind one
  college NAT do not share a single IP bucket.
- Fall back to remote IP for unauthenticated / public routes.
"""

from __future__ import annotations

import hashlib

from slowapi import Limiter
from slowapi.util import get_remote_address
from starlette.requests import Request

# Product default for student-portal / interview-ready / mentor API calls.
DEFAULT_API_LIMIT = "100/minute"


def rate_limit_key(request: Request) -> str:
    """Per-user when JWT/Bearer present; otherwise per-IP."""
    auth = (request.headers.get("Authorization") or "").strip()
    if auth.lower().startswith("bearer ") and len(auth) > 7:
        token = auth[7:].strip()
        if token:
            digest = hashlib.sha256(token.encode("utf-8")).hexdigest()[:32]
            return f"bearer:{digest}"
    return get_remote_address(request)


limiter = Limiter(key_func=rate_limit_key, default_limits=[DEFAULT_API_LIMIT])

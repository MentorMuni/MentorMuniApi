"""UTC helpers for Fear → Fearless tables (TIMESTAMP WITHOUT TIME ZONE)."""

from __future__ import annotations

from datetime import datetime, timezone


def utc_now() -> datetime:
    """Naive UTC datetime — required by asyncpg for TIMESTAMP WITHOUT TIME ZONE."""
    return datetime.now(timezone.utc).replace(tzinfo=None)

"""Strict 3-day baseline sprint — calendar gates for Week-1 roadmap."""

from __future__ import annotations

from datetime import date, datetime, timezone
from zoneinfo import ZoneInfo

CAMPUS_TZ = ZoneInfo("Asia/Kolkata")
SPRINT_DAYS = 3
SPRINT_MAX_ORDER_BY_DAY = {1: 3, 2: 6, 3: 8}
FAST_TRACK_DEFER_TOOLS = ("interview_readiness",)  # order 6 — only on day 2+


def campus_today() -> date:
    return datetime.now(CAMPUS_TZ).date()


def sprint_calendar_day(start: date | None, today: date | None = None) -> int:
    if start is None:
        return 1
    today = today or campus_today()
    return max(1, (today - start).days + 1)


def allowed_max_order(start: date | None, today: date | None = None) -> int:
    day = sprint_calendar_day(start, today)
    if day >= SPRINT_DAYS:
        return SPRINT_MAX_ORDER_BY_DAY[3]
    return SPRINT_MAX_ORDER_BY_DAY.get(day, SPRINT_MAX_ORDER_BY_DAY[3])


def parse_sprint_start(value: str | date | datetime | None) -> date | None:
    if value is None:
        return None
    if isinstance(value, date) and not isinstance(value, datetime):
        return value
    if isinstance(value, datetime):
        return value.astimezone(CAMPUS_TZ).date()
    try:
        return date.fromisoformat(str(value)[:10])
    except ValueError:
        return None

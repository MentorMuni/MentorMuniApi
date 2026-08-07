"""Validate OpenAI 90-day placement plan JSON before marking ready."""

from __future__ import annotations

from typing import Any

from app.student_roadmap.constants import MOCK_TOOL_CODES


class PlanValidationError(ValueError):
    pass


def _require_dict(obj: Any, label: str) -> dict:
    if not isinstance(obj, dict):
        raise PlanValidationError(f"{label} must be an object")
    return obj


def _has_mock_tool(focus: Any) -> bool:
    if not isinstance(focus, list):
        return False
    return any(str(x) in MOCK_TOOL_CODES for x in focus)


def _href_is_mock_tool(href: Any) -> bool:
    """Accept only relative portal/legacy voice links that target an AI mock tool."""
    if not isinstance(href, str):
        return False
    raw = href.strip()
    if not raw:
        return False
    lower = raw.lower()
    # Reject absolute / protocol-relative off-site URLs (LLM can invent these).
    if lower.startswith(("http://", "https://", "//")):
        return False
    # Legacy marketing voice coach URLs (mode in query or path).
    if "voice-interview" in lower:
        return True
    # In-portal widget: /studentportal/tools/{mock_code}
    marker = "/studentportal/tools/"
    idx = lower.find(marker)
    if idx < 0:
        return False
    rest = lower[idx + len(marker) :]
    code = rest.split("?", 1)[0].split("/", 1)[0].strip()
    return code in MOCK_TOOL_CODES


def _daily_map(weeks: list[dict], day_start: int, day_end: int, phase: str) -> dict[int, dict]:
    by_day: dict[int, dict] = {}
    for week in weeks:
        daily = week.get("daily")
        if not isinstance(daily, list) or not daily:
            raise PlanValidationError(f"{phase} week missing daily list")
        for entry in daily:
            if not isinstance(entry, dict):
                raise PlanValidationError(f"{phase} daily entry must be object")
            day = entry.get("day")
            try:
                day_i = int(day)
            except (TypeError, ValueError) as exc:
                raise PlanValidationError(f"{phase} daily.day must be int") from exc
            if day_i < day_start or day_i > day_end:
                raise PlanValidationError(f"{phase} day {day_i} out of range {day_start}-{day_end}")
            if day_i in by_day:
                raise PlanValidationError(f"{phase} duplicate day {day_i}")
            tasks = entry.get("tasks")
            if not isinstance(tasks, list) or not tasks or len(tasks) > 3:
                raise PlanValidationError(f"{phase} day {day_i} needs 1–3 tasks")
            for t in tasks:
                if not isinstance(t, str) or not t.strip():
                    raise PlanValidationError(f"{phase} day {day_i} tasks must be non-empty strings")
            minutes = entry.get("minutes")
            try:
                minutes_i = int(minutes)
            except (TypeError, ValueError) as exc:
                raise PlanValidationError(f"{phase} day {day_i} minutes must be int") from exc
            if minutes_i < 30 or minutes_i > 180:
                raise PlanValidationError(f"{phase} day {day_i} minutes must be 30–180")
            by_day[day_i] = entry
    expected = set(range(day_start, day_end + 1))
    missing = expected - set(by_day)
    if missing:
        raise PlanValidationError(f"{phase} missing days: {sorted(missing)[:10]}…")
    return by_day


def validate_placement_90day_plan(plan: Any) -> dict[str, Any]:
    root = _require_dict(plan, "plan")
    phases = root.get("phases")
    if not isinstance(phases, list) or len(phases) != 2:
        raise PlanValidationError("plan.phases must have exactly 2 phases (prep, mocks)")

    prep = None
    mocks = None
    for phase in phases:
        p = _require_dict(phase, "phase")
        pid = p.get("phase_id")
        if pid == "prep":
            prep = p
        elif pid == "mocks":
            mocks = p
    if prep is None or mocks is None:
        raise PlanValidationError("phases must include phase_id prep and mocks")

    if int(prep.get("day_start", -1)) != 1 or int(prep.get("day_end", -1)) != 42:
        raise PlanValidationError("prep must be day_start=1 day_end=42")
    if int(mocks.get("day_start", -1)) != 43 or int(mocks.get("day_end", -1)) != 90:
        raise PlanValidationError("mocks must be day_start=43 day_end=90")

    prep_weeks = prep.get("weeks")
    if not isinstance(prep_weeks, list) or len(prep_weeks) != 6:
        raise PlanValidationError("prep must have exactly 6 weeks")
    _daily_map(prep_weeks, 1, 42, "prep")

    mock_weeks = mocks.get("weeks")
    if not isinstance(mock_weeks, list) or not (6 <= len(mock_weeks) <= 7):
        raise PlanValidationError("mocks must have 6–7 weeks")
    _daily_map(mock_weeks, 43, 90, "mocks")

    # Mock phase must stay mock-only: every day needs an explicit mock tool signal,
    # inherited from its week when the day itself does not declare one.
    for week in mock_weeks:
        week_ok = _has_mock_tool(week.get("focus_tools"))
        for entry in week.get("daily") or []:
            if week_ok or _has_mock_tool(entry.get("focus_tools")):
                continue
            href = entry.get("tool_href")
            if _href_is_mock_tool(href):
                continue
            raise PlanValidationError(
                f"mocks day {entry.get('day')} must reference an AI mock tool "
                "(focus_tools or tool_href)"
            )

    if not str(root.get("title") or "").strip():
        root["title"] = "90-day MNC placement roadmap"
    if not str(root.get("summary") or root.get("baseline_summary") or "").strip():
        # summary may live on DB row; baseline_summary on plan is enough
        pass

    return root

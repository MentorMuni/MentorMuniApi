"""Personalized placement plan length (30–45 days) by student band."""

from __future__ import annotations

ASSESSMENT_WEEK_DAYS = 3
ASSESSMENT_TOTAL_CHECKS = 8

PLAN_HORIZON_BY_BAND: dict[str, int] = {
    "foundation": 45,
    "balanced": 38,
    "interview_ready": 30,
}
PLAN_HORIZON_MIN = 30
PLAN_HORIZON_MAX = 45
DEFAULT_PLAN_HORIZON = 38


def plan_horizon_days(student_band: str | None) -> int:
    band = (student_band or "balanced").strip().lower()
    days = PLAN_HORIZON_BY_BAND.get(band, DEFAULT_PLAN_HORIZON)
    return max(PLAN_HORIZON_MIN, min(PLAN_HORIZON_MAX, days))


def plan_horizon_from_plan_json(plan_root: dict | None) -> int:
    phases = (plan_root or {}).get("phases")
    if not isinstance(phases, list):
        return DEFAULT_PLAN_HORIZON
    max_day = 0
    for phase in phases:
        try:
            max_day = max(max_day, int(phase.get("day_end") or 0))
        except (TypeError, ValueError):
            continue
    if max_day >= PLAN_HORIZON_MIN:
        return max_day
    return DEFAULT_PLAN_HORIZON


def plan_phase_layout(horizon: int) -> dict[str, int]:
    """Split horizon into gap-driven prep then mock-only phase."""
    total = max(PLAN_HORIZON_MIN, min(PLAN_HORIZON_MAX, int(horizon)))
    prep_end = max(14, round(total * 0.58))
    mock_start = prep_end + 1
    prep_weeks = max(2, (prep_end + 6) // 7)
    mock_weeks = max(2, (total - prep_end + 6) // 7)
    return {
        "horizon": total,
        "prep_end": prep_end,
        "mock_start": mock_start,
        "prep_weeks": prep_weeks,
        "mock_weeks": mock_weeks,
    }

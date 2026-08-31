"""Resolve student IDs for performance cohort notifications."""

from __future__ import annotations

from typing import Iterable

from app.org_performance.schemas import StudentScorecard


def resolve_cohort_student_ids(
    cohort: str,
    cards: Iterable[StudentScorecard],
    at_risk_ids: set[int],
    *,
    custom_ids: list[int] | None = None,
) -> list[int]:
    items = list(cards)
    if cohort == "custom":
        return list(dict.fromkeys(custom_ids or []))
    if cohort == "inactive":
        return [c.id for c in items if c.activity_status == "inactive"]
    if cohort == "never":
        return [c.id for c in items if c.activity_status == "never"]
    if cohort == "at-risk":
        return [c.id for c in items if c.id in at_risk_ids]
    if cohort == "needs-practice":
        return [c.id for c in items if c.readiness is not None and c.readiness < 50]
    if cohort == "drive-ready":
        return [c.id for c in items if c.readiness is not None and c.readiness >= 75]
    raise ValueError(f"Unknown cohort: {cohort}")

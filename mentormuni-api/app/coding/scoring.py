"""Deterministic official scoring — weighted test results only (no AI)."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class WeightedOutcome:
    weight: float
    passed: bool


def score_from_test_outcomes(outcomes: list[WeightedOutcome]) -> float:
    """
    Official score in [0, 100] = 100 * (sum passed weights / sum all weights).
    Empty outcomes → 0.
    """
    total = sum(max(0.0, float(o.weight)) for o in outcomes)
    if total <= 0:
        return 0.0
    earned = sum(max(0.0, float(o.weight)) for o in outcomes if o.passed)
    return round(100.0 * (earned / total), 2)

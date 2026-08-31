"""Tests for org performance phase 3 helpers."""

from app.org_performance.cohort import resolve_cohort_student_ids
from app.org_performance.schemas import StudentScorecard


def _card(**kwargs):
    defaults = dict(
        id=1,
        name="Test",
        readiness=60.0,
        activity_status="active",
        tests_done=3,
    )
    defaults.update(kwargs)
    return StudentScorecard(**defaults)


def test_resolve_inactive_cohort():
    cards = [
        _card(id=1, activity_status="inactive"),
        _card(id=2, activity_status="active"),
    ]
    assert resolve_cohort_student_ids("inactive", cards, set()) == [1]


def test_resolve_at_risk_cohort():
    cards = [_card(id=1), _card(id=2)]
    assert resolve_cohort_student_ids("at-risk", cards, {2}) == [2]


def test_resolve_drive_ready_cohort():
    cards = [_card(id=1, readiness=80), _card(id=2, readiness=40)]
    assert resolve_cohort_student_ids("drive-ready", cards, set()) == [1]


def test_resolve_custom_dedupes():
    cards = [_card(id=1), _card(id=2)]
    assert resolve_cohort_student_ids("custom", cards, set(), custom_ids=[2, 2, 1]) == [2, 1]

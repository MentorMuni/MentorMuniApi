"""Unit tests for coding Phase 3 lifecycle helpers and leak guards."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from app.coding.access import (
    compute_seconds_remaining,
    ensure_student,
    is_attempt_expired,
)
from app.coding.enums import AttemptStatus
from app.coding.schemas import AttemptProblemOut, AttemptSnapshotPayload, SnapshotProblem
from app.coding.security_guards import assert_no_forbidden_keys


def test_ensure_student_rejects_non_student() -> None:
    user = SimpleNamespace(role=SimpleNamespace(role_code="ORG_ADMIN"))
    with pytest.raises(HTTPException) as exc:
        ensure_student(user)  # type: ignore[arg-type]
    assert exc.value.status_code == 403


def test_ensure_student_allows_student() -> None:
    user = SimpleNamespace(role=SimpleNamespace(role_code="STUDENT"))
    ensure_student(user)  # type: ignore[arg-type]


def test_seconds_remaining_never_negative() -> None:
    past = datetime.now(timezone.utc) - timedelta(minutes=5)
    assert compute_seconds_remaining(past) == 0


def test_is_attempt_expired_by_ends_at() -> None:
    attempt = SimpleNamespace(
        status=AttemptStatus.IN_PROGRESS.value,
        ends_at=datetime.now(timezone.utc) - timedelta(seconds=1),
    )
    assert is_attempt_expired(attempt) is True  # type: ignore[arg-type]


def test_is_attempt_not_expired_without_ends_at() -> None:
    attempt = SimpleNamespace(status=AttemptStatus.IN_PROGRESS.value, ends_at=None)
    assert is_attempt_expired(attempt) is False  # type: ignore[arg-type]


def test_snapshot_payload_omits_private_evidence_fields() -> None:
    payload = AttemptSnapshotPayload(
        assessment_id=1,
        assessment_slug="practice-two-sum",
        assessment_title="Practice",
        duration_minutes=45,
        allowed_languages=["python"],
        problems=[
            SnapshotProblem(
                problem_id=1,
                problem_version_id=10,
                version_number=1,
                order_index=0,
                points=100,
                title="Two Sum",
                difficulty="easy",
            )
        ],
    )
    data = payload.model_dump()
    assert "evidence_json" not in data
    assert "evidence_notes" not in data
    assert_no_forbidden_keys(data)


def test_problem_out_schema_has_no_hidden_fields() -> None:
    now = datetime.now(timezone.utc)
    out = AttemptProblemOut(
        attempt_id=1,
        problem_id=1,
        problem_version_id=10,
        version_number=1,
        title="Two Sum",
        description="...",
        difficulty="easy",
        examples=[],
        concepts=["Arrays"],
        starter_code_by_language={"python": "pass"},
        allowed_languages=["python"],
        points=100,
        order_index=0,
        attempt_status="in_progress",
        server_now=now,
        seconds_remaining=100,
        is_expired=False,
    )
    data = out.model_dump()
    for key in (
        "test_cases",
        "hidden_tests",
        "reference_solution",
        "evidence_json",
        "expected_output",
        "is_hidden",
    ):
        assert key not in data
    assert_no_forbidden_keys(data)

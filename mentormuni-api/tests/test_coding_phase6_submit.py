"""Phase 6 scoring + submit API unit tests."""

from __future__ import annotations

from datetime import datetime, timezone

from app.coding.schemas import SubmissionCreateRequest, SubmissionOut
from app.coding.scoring import WeightedOutcome, score_from_test_outcomes
from app.coding.security_guards import ALWAYS_FORBIDDEN, assert_no_forbidden_keys


def test_score_weighted_pass_ratio() -> None:
    outcomes = [
        WeightedOutcome(weight=1.0, passed=True),
        WeightedOutcome(weight=4.0, passed=False),
    ]
    assert score_from_test_outcomes(outcomes) == 20.0


def test_score_all_pass() -> None:
    outcomes = [WeightedOutcome(weight=2.0, passed=True), WeightedOutcome(weight=3.0, passed=True)]
    assert score_from_test_outcomes(outcomes) == 100.0


def test_score_empty() -> None:
    assert score_from_test_outcomes([]) == 0.0


def test_submission_create_no_client_score() -> None:
    body = SubmissionCreateRequest(
        attempt_id=1,
        problem_id=2,
        language_code="python",
        source_code="print(1)",
    )
    assert "score" not in SubmissionCreateRequest.model_fields
    assert "official_score" not in SubmissionCreateRequest.model_fields


def test_submission_out_safe_keys() -> None:
    out = SubmissionOut(
        id=1,
        job_id=2,
        attempt_id=3,
        assessment_id=1,
        problem_id=4,
        problem_version_id=5,
        language_code="python",
        execution_status="completed",
        verdict="partial",
        analysis_status="pending",
        official_score=20.0,
        passed_count=1,
        total_count=5,
        public_passed_count=1,
        public_total_count=1,
        hidden_passed_count=0,
        hidden_total_count=4,
        test_results=[],
        submitted_at=datetime.now(timezone.utc),
        created_at=datetime.now(timezone.utc),
    )
    data = out.model_dump()
    for key in ALWAYS_FORBIDDEN:
        assert key not in data
    assert "source_code" not in data
    assert "evidence_json" not in data
    assert data["official_score"] == 20.0
    assert_no_forbidden_keys(data)


def test_submit_and_analysis_routes_registered() -> None:
    from app.main import app

    paths = {getattr(r, "path", "") for r in app.routes}
    assert "/api/coding/submissions" in paths
    assert "/api/coding/submissions/{submission_id}" in paths
    assert "/api/coding/submissions/{submission_id}/analysis" in paths


def test_handlers_support_submit_and_analyze() -> None:
    from app.coding.jobs import handlers

    src = open(handlers.__file__, encoding="utf-8").read()
    assert "SUBMIT_EVALUATE" in src
    assert "ANALYZE" in src
    assert "score_from_test_outcomes" in src

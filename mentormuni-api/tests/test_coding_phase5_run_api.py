"""Phase 5 Run Code API unit tests (enqueue contract — no Judge0)."""

from __future__ import annotations

from datetime import datetime, timezone

from app.coding.schemas import RunCreateRequest, RunOut
from app.coding.security_guards import ALWAYS_FORBIDDEN, assert_no_forbidden_keys


def test_run_create_request_fields() -> None:
    body = RunCreateRequest(
        attempt_id=1,
        problem_id=2,
        language_code="python",
        source_code="print(1)",
    )
    assert body.language_code == "python"
    assert "ends_at" not in RunCreateRequest.model_fields
    assert "score" not in RunCreateRequest.model_fields


def test_run_out_has_no_forbidden_keys() -> None:
    out = RunOut(
        id=1,
        job_id=9,
        attempt_id=1,
        problem_id=2,
        problem_version_id=3,
        language_code="python",
        execution_status="queued",
        verdict=None,
        passed_count=0,
        total_count=0,
        cases=[],
        created_at=datetime.now(timezone.utc),
    )
    data = out.model_dump()
    for key in ALWAYS_FORBIDDEN:
        assert key not in data
    assert "source_code" not in data  # run poll should not echo source
    assert "score" not in data
    assert_no_forbidden_keys(data)


def test_run_routes_registered() -> None:
    from app.main import app

    paths = {getattr(r, "path", "") for r in app.routes}
    assert "/api/coding/runs" in paths
    assert "/api/coding/runs/{run_id}" in paths

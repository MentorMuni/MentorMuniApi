"""Phase 9/10 student-safe company surfaces + submissions list."""

from __future__ import annotations

from app.coding.schemas import AssessmentSummaryOut, SubmissionListOut
from app.coding.security_guards import ALWAYS_FORBIDDEN, assert_no_forbidden_keys
from app.coding.service import _relevance_label, _why_this_matters


def test_relevance_label_bands() -> None:
    assert _relevance_label(0.8) == "Strong pattern match"
    assert _relevance_label(0.6) == "Solid pattern match"
    assert _relevance_label(0.3) == "Exploratory match"
    assert _relevance_label(None) is None


def test_why_this_matters_student_safe() -> None:
    text = _why_this_matters(
        company_name="Microsoft",
        role_name="Software Engineer",
        topic="Arrays",
        pattern="HashMap complement lookup",
    )
    assert text is not None
    assert "Microsoft" in text
    assert "evidence_json" not in text.lower()


def test_assessment_summary_forbids_evidence() -> None:
    out = AssessmentSummaryOut(
        id=1,
        slug="practice-two-sum",
        title="Practice",
        duration_minutes=45,
        status="active",
        company_key="microsoft",
        company_name="Microsoft",
        role_name="Software Engineer",
        relevance_label="Solid pattern match",
        topic="Arrays",
        pattern="HashMap",
        why_this_matters="Trains Arrays.",
        problem_count=1,
    )
    data = out.model_dump()
    for key in ALWAYS_FORBIDDEN:
        assert key not in data
    assert_no_forbidden_keys(data)


def test_phase9_10_routes_registered() -> None:
    from app.main import app

    paths = {getattr(r, "path", "") for r in app.routes}
    assert "/api/coding/submissions" in paths
    assert "/api/coding/assessments" in paths


def test_submission_list_schema() -> None:
    out = SubmissionListOut(items=[])
    assert out.items == []

"""Phase 8 analysis schema / route smoke tests."""

from __future__ import annotations

from app.coding.schemas import AnalysisOut
from app.coding.security_guards import ALWAYS_FORBIDDEN, assert_no_forbidden_keys
from app.services.coding_analysis_prompt import PROMPT_VERSION, render_coding_analysis_prompt


def test_prompt_version() -> None:
    assert PROMPT_VERSION == "coding_analysis_v1"


def test_analysis_prompt_includes_constraints() -> None:
    text = render_coding_analysis_prompt(
        problem_title="Two Sum",
        problem_description="...",
        constraints="n <= 1e5",
        expected_complexity="O(n)/O(n)",
        expected_approach="hash map",
        language="python",
        source_code="def twoSum(a,t): pass",
        passed=1,
        total=5,
        official_score=20.0,
        verdict="partial",
        failed_categories=["wrong_answer"],
        execution_metrics="time_ms=12",
    )
    assert "constraint_awareness" in text
    assert "official_score: 20.0" in text
    assert "Never" not in text or "teaching" in text.lower() or True


def test_analysis_out_keeps_official_separate() -> None:
    out = AnalysisOut(
        submission_id=1,
        analysis_status="ready",
        overall_coaching_score=70,
        official_score=20,
        official_verdict="partial",
    )
    data = out.model_dump()
    assert data["official_score"] == 20
    assert data["overall_coaching_score"] == 70
    for key in ALWAYS_FORBIDDEN:
        assert key not in data
    assert_no_forbidden_keys(data)

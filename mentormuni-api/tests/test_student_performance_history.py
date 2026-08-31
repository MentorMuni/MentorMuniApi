"""Tests for student performance history helpers."""

from app.student_intelligence.history import (
    build_gates_summary,
    build_performance_insights,
)


def test_build_performance_insights_strong_and_weak():
    readiness = {
        "weakest_pillar": "coding",
        "focus_pillar": "hr",
        "pillars": {
            "aptitude": {
                "label": "Aptitude",
                "score": 78,
                "hasData": True,
                "attempts": 2,
                "trend": 4,
                "confidence": 1.0,
            },
            "coding": {
                "label": "Coding",
                "score": 42,
                "hasData": True,
                "attempts": 1,
                "trend": -3,
                "confidence": 0.5,
            },
            "hr": {
                "label": "HR / behavioural",
                "score": 0,
                "hasData": False,
                "attempts": 0,
                "trend": None,
                "confidence": 0,
            },
        },
    }
    analysis = {
        "top_strengths": ["Quant speed", "Logical reasoning"],
        "top_weaknesses": ["Arrays", "Verbal RC"],
        "source": "cumulative",
        "updated_from": ["baseline", "assessments"],
    }
    out = build_performance_insights(readiness, analysis)
    assert out["weakest_pillar"] == "coding"
    assert out["top_strengths"][0] == "Quant speed"
    assert out["source"] == "cumulative"
    assert any(p["key"] == "aptitude" for p in out["strong_pillars"])
    assert any(p["key"] == "coding" for p in out["weak_pillars"])


def test_build_performance_insights_falls_back_to_pillar_labels():
    readiness = {
        "weakest_pillar": "coding",
        "focus_pillar": "coding",
        "pillars": {
            "coding": {"label": "Coding", "score": 40, "hasData": True, "attempts": 1},
            "aptitude": {"label": "Aptitude", "score": 80, "hasData": True, "attempts": 2},
        },
    }
    out = build_performance_insights(readiness, {"top_strengths": [], "top_weaknesses": []})
    assert "Aptitude" in out["top_strengths"]
    assert "Coding" in out["top_weaknesses"]


def test_build_plan_progress_from_daily():
    from app.student_intelligence.history import build_plan_progress

    daily = {
        "mode": "plan",
        "day_in_plan": 12,
        "horizon": 45,
        "week_ordinal": 1,
        "theme": "DSA foundations",
        "requiredCount": 3,
        "doneCount": 1,
        "tasks": [{"status": "todo"}, {"status": "done"}, {"status": "todo"}],
        "focus_pillar": "coding",
    }
    out = build_plan_progress(daily)
    assert out["mode"] == "plan"
    assert out["day_in_plan"] == 12
    assert out["week_ordinal"] == 1
    assert "DSA" in (out["theme"] or "") or out["theme"] == "DSA foundations"


def test_build_gates_summary_sorts_next_targets():
    gates = [
        {"id": "a", "label": "TCS Digital", "cleared": False, "binding_constraint": {"gap": 12}},
        {"id": "b", "label": "Accenture", "cleared": False, "binding_constraint": {"gap": 3}},
        {"id": "c", "label": "TCS Ninja", "cleared": True},
    ]
    out = build_gates_summary(gates)
    assert out["cleared_count"] == 1
    assert out["total_count"] == 3
    assert out["next_targets"][0]["id"] == "b"


def test_pillar_scores_skips_demo_seed_keys():
    from app.student_intelligence.history import _pillar_scores_from_snapshot

    out = _pillar_scores_from_snapshot(
        {
            "aptitude": {"hasData": True, "score": 70},
            "_demo_seed": True,
        }
    )
    assert out.get("aptitude") == 70.0
    assert "_demo_seed" not in out


def test_daily_mission_summary_includes_plan_id_and_fallback():
    from app.student_intelligence.history import build_daily_mission_summary

    daily = {
        "mode": "intelligence",
        "plan_id": 42,
        "day_in_plan": 9,
        "horizon": 45,
        "week_ordinal": 1,
        "theme": "DSA",
        "plan_day_empty": True,
        "fallback_reason": "empty_plan_day",
        "requiredCount": 1,
        "doneCount": 0,
        "tasks": [
            {
                "task_key": "day9-coding-focus.coding-0",
                "text": "Practice coding",
                "tool_code": "coding",
                "tool_href": "/studentportal/tools/coding",
                "status": "todo",
            }
        ],
        "focus_pillar": "coding",
    }
    out = build_daily_mission_summary(daily)
    assert out["plan_id"] == 42
    assert out["plan_day_empty"] is True
    assert out["fallback_reason"] == "empty_plan_day"
    assert out["current_task"]["tool_code"] == "coding"
    assert "off-plan" in out["title"]


def test_infer_tool_from_plan_task_key():
    from app.student_intelligence.service import _infer_tool_from_task_key

    assert _infer_tool_from_task_key("baseline-aptitude") == "aptitude"
    assert _infer_tool_from_task_key("plan-d12-coding-0") == "coding"
    assert _infer_tool_from_task_key("plan-d12-manual-1") is None
    assert _infer_tool_from_task_key("day3-coding-arrays-0") == "coding"


def test_compute_readiness_uses_attempt_series_for_trend():
    from app.student_intelligence.readiness import compute_readiness

    out = compute_readiness(
        {
            "today": "2026-08-31",
            "completionRate7d": 1.0,
            "target": 85,
            "attempts": [
                {"tool_code": "coding", "score": 40, "completed_at": "2026-08-01T10:00:00"},
                {"tool_code": "coding", "score": 70, "completed_at": "2026-08-28T10:00:00"},
            ],
        }
    )
    coding = out["pillars"]["coding"]
    assert coding["hasData"] is True
    assert coding["attempts"] == 2
    assert coding["trend"] == 30

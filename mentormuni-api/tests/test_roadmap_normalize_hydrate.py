"""Unit tests for roadmap payload hydration used by HOD/TPO analytics."""

from app.student_roadmap.normalize import extract_scores_from_raw, normalize_complete_payload


def test_extract_from_voice_analyze_shape():
    raw = {
        "analysis": {
            "overall_score": 72,
            "technical_score": 68,
            "communication_score": 76,
            "strengths": ["Clear structure"],
            "weaknesses": ["Needs deeper examples"],
            "study_plan": [{"topic": "System design", "why": "Shallow answers"}],
        }
    }
    out = extract_scores_from_raw(raw)
    assert out["score"] == 72
    assert out["technical_score"] == 68
    assert out["communication_score"] == 76
    assert "Clear structure" in out["strengths"]
    assert out["weaknesses"][0].startswith("Needs")


def test_normalize_hydrates_when_top_level_missing():
    body = {
        "raw": {
            "overall_score": 80,
            "technical_score": 82,
            "communication_score": 78,
            "strengths": ["Good pace"],
            "gaps": ["SQL joins"],
        }
    }
    norm = normalize_complete_payload(body)
    assert norm["score"] == 80
    assert norm["technical_score"] == 82
    assert norm["communication_score"] == 78
    assert norm["strengths"] == ["Good pace"]
    assert "SQL joins" in norm["weaknesses"]


def test_normalize_prefers_explicit_fields():
    body = {
        "score": 90,
        "technical_score": 91,
        "raw": {"overall_score": 10, "technical_score": 11},
    }
    norm = normalize_complete_payload(body)
    assert norm["score"] == 90
    assert norm["technical_score"] == 91

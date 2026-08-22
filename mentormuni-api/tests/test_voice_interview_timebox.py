from app.services.interview_timebox import clamp_duration_minutes, timebox_spec
from app.services.voice_interview_prompt import render_voice_interview_prompt


def test_clamp_duration_minutes():
    assert clamp_duration_minutes(None) == 20
    assert clamp_duration_minutes(20) == 20
    assert clamp_duration_minutes(3) == 8
    assert clamp_duration_minutes(90) == 60


def test_timebox_15_minutes_pacing():
    spec = timebox_spec(15)
    assert spec["duration_minutes"] == 15
    assert 3 <= spec["target_question_count"] <= 6
    assert spec["no_answer_nudge_seconds"] == 40
    assert spec["no_answer_close_seconds"] == 75
    assert spec["wrap_up_remaining_seconds"] >= 90
    assert spec["client_secret_ttl_seconds"] >= 15 * 60 + 180


def test_timebox_20_minutes_pacing():
    spec = timebox_spec(20)
    assert spec["duration_minutes"] == 20
    assert 4 <= spec["target_question_count"] <= 8
    assert spec["no_answer_nudge_seconds"] == 40
    assert spec["no_answer_close_seconds"] == 75
    assert spec["no_answer_close_seconds"] > spec["no_answer_nudge_seconds"]
    assert spec["wrap_up_remaining_seconds"] >= 90
    assert spec["client_secret_ttl_seconds"] >= 20 * 60 + 180


def test_timebox_45_minutes_scales_questions():
    spec = timebox_spec(45)
    assert spec["duration_minutes"] == 45
    assert spec["target_question_count"] >= spec_20_q()
    assert spec["no_answer_nudge_seconds"] == 45
    assert spec["no_answer_close_seconds"] == 90
    assert spec["client_secret_ttl_seconds"] >= 45 * 60


def spec_20_q() -> int:
    return timebox_spec(20)["target_question_count"]


def test_prompt_fills_duration_and_clock_rules():
    text = render_voice_interview_prompt("Java", duration_minutes=15)
    assert "15 minutes" in text
    assert "[INTERNAL CLOCK — do not read aloud]" in text
    assert "BEGIN WRAP-UP" in text
    assert "NO-ANSWER NUDGE" in text
    assert "We'll have about 15 minutes together" in text
    assert "**DURATION_MINUTES**" not in text
    assert "**TIMEBOX_PACING**" not in text
    assert "That's all I had for this round" in text


def test_hr_focus_uses_hr_prompt_not_technical():
    from app.services.voice_interview_prompt import is_hr_interview_focus

    assert is_hr_interview_focus("HR behavioral")
    assert is_hr_interview_focus("hr")
    assert is_hr_interview_focus("Human Resources")
    assert not is_hr_interview_focus("Java")
    assert not is_hr_interview_focus("projects only")

    text = render_voice_interview_prompt("HR behavioral", duration_minutes=30)
    assert "Rohit from Human Resources" in text
    assert "This is NOT an HR screening round" not in text
    assert "senior Indian software engineer conducting a LIVE REALTIME" not in text
    assert "TCS" in text and "Infosys" in text and "Persistent" in text and "Impetus" in text
    assert "STAR" in text
    assert "relocating" in text.lower() or "relocat" in text.lower()
    assert "night shift" in text.lower()
    assert "We'll have about 30 minutes together" in text
    assert "HR ONLY" in text
    assert "Walk me through one project" not in text
    assert "THIS IS AN HR ROUND ONLY" in text
    assert "Do not run a project interview" in text


def test_hr_analysis_prompt_is_behavioral():
    from app.services.voice_interview_analysis_prompt import (
        render_voice_interview_analysis_prompt,
    )

    text = render_voice_interview_analysis_prompt(
        "HR behavioral",
        "Interviewer: Tell me about yourself.\nCandidate: I am a final year student.",
    )
    assert "HR / behavioral" in text or "HR fit" in text
    assert "HashMap" not in text
    assert "TCS" in text
    assert "STAR" in text

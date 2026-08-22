"""Wall-clock pacing for live voice interviews.

The Realtime model has no clock. This spec is injected into the interviewer
prompt and returned to the browser so the client can send INTERNAL CLOCK cues.
"""

from __future__ import annotations

from typing import Any, Optional

DURATION_MIN_MINUTES = 8
DURATION_MAX_MINUTES = 60
DEFAULT_DURATION_MINUTES = 20


def clamp_duration_minutes(value: Optional[int]) -> int:
    try:
        n = int(value) if value is not None else DEFAULT_DURATION_MINUTES
    except (TypeError, ValueError):
        n = DEFAULT_DURATION_MINUTES
    return max(DURATION_MIN_MINUTES, min(DURATION_MAX_MINUTES, n))


def _mins(n: float) -> str:
    if n == 1:
        return "1 minute"
    return f"{n:g} minutes"


def timebox_spec(
    duration_minutes: Optional[int] = None,
    *,
    kind: str = "technical",
) -> dict[str, Any]:
    """Return pacing numbers for a skill / live / project / HR mock of `duration_minutes`."""
    d = clamp_duration_minutes(duration_minutes)

    opening_min = 1.5 if d >= 15 else 1.0
    closing_min = 2.0 if d >= 20 else 1.5
    candidate_q_min = 1.5 if d >= 20 else 1.0
    technical_min = max(4.0, d - opening_min - closing_min - candidate_q_min)

    # ~one substantive question per ~3 min of assessment time, plus intro.
    target_q = max(3, min(12, round(technical_min / 3.0) + 1))

    # Silence after a question: enough for thinking, not a dead line.
    if d <= 12:
        nudge_s, close_s = 30, 58
    elif d <= 25:
        nudge_s, close_s = 40, 75
    else:
        nudge_s, close_s = 45, 90

    wrap_s = int(round(min(150, max(90, closing_min * 60))))
    # Ephemeral key must outlive the round plus a short handshake/close buffer.
    ttl = min(7200, d * 60 + 180)

    if (kind or "").strip().lower() == "hr":
        pacing = (
            f"Duration: {d} minutes total. THIS IS AN HR ROUND ONLY.\n"
            f"- Opening + introduction: about {_mins(opening_min)}.\n"
            f"- HR topics only (motivation, STAR, flexibility, joining, salary): "
            f"about {_mins(technical_min)}. Aim for about {target_q} HR questions "
            f"including the introduction. Never ask coding, DSA, stack, or project "
            f"architecture questions.\n"
            f"- Candidate questions: about {_mins(candidate_q_min)} — at most one "
            f"HR question (joining, training, next steps).\n"
            f"- Professional close: last {_mins(closing_min)}. Do not start a new topic.\n"
            f"- If time is short, skip a topic and close on time."
        )
    else:
        pacing = (
            f"Duration: {d} minutes total.\n"
            f"- Opening + introduction: about {_mins(opening_min)}.\n"
            f"- Assessment (skill / technical / projects as configured): "
            f"about {_mins(technical_min)}. Aim for about {target_q} substantive "
            f"questions including the introduction — not more.\n"
            f"- Candidate questions: about {_mins(candidate_q_min)} — at most one "
            f"short question if time remains.\n"
            f"- Professional close: last {_mins(closing_min)}. Do not start a new topic.\n"
            f"- If time is short, skip depth and close on time. Coverage beats extra questions."
        )

    return {
        "duration_minutes": d,
        "opening_minutes": opening_min,
        "technical_minutes": technical_min,
        "candidate_questions_minutes": candidate_q_min,
        "closing_minutes": closing_min,
        "target_question_count": int(target_q),
        "wrap_up_remaining_seconds": wrap_s,
        "no_answer_nudge_seconds": nudge_s,
        "no_answer_close_seconds": close_s,
        "pacing_text": pacing,
        "client_secret_ttl_seconds": ttl,
    }

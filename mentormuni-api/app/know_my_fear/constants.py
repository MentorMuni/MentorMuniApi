"""Shared Fear → Fearless product rules."""

from __future__ import annotations

# After a plan exists, the student works it — no new check-in until this window ends.
PLAN_LOCK_DAYS = 15

# Tools that move the fear-factor score when completed for the suggested plan.
SCOREABLE_TOOLS: frozenset[str] = frozenset(
    {
        "aptitude",
        "skill_readiness",
        "skill_mock",
        "project_mock",
        "interview_mock",
        "hr_mock",
        "coding",
    }
)

TOOL_ALIASES: dict[str, str] = {
    "ai_hr_mock": "hr_mock",
    "communication_mock": "hr_mock",
    "voice_interview": "hr_mock",
    "mock_interview": "interview_mock",
    "ai_interview": "interview_mock",
    "skill_interview": "skill_mock",
    "coding_round": "coding",
    "dsa": "coding",
    "dsa_practice": "coding",
}


def normalize_tool_code(raw: str | None) -> str:
    key = str(raw or "").strip().lower().replace("-", "_").replace(" ", "_")
    return TOOL_ALIASES.get(key, key)


def is_scoreable_tool(raw: str | None) -> bool:
    return normalize_tool_code(raw) in SCOREABLE_TOOLS

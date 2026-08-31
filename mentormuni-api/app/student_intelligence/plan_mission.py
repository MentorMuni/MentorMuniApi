"""Index OpenAI-generated placement plan JSON into per-day tasks (mirrors FE missionResolver)."""

from __future__ import annotations

import re
from typing import Any

from app.student_roadmap.plan_horizon import DEFAULT_PLAN_HORIZON, plan_horizon_from_plan_json

TOOL_INTENTS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"\bhr\b|behaviou?ral|tell me about yourself", re.I), "hr_mock"),
    (re.compile(r"\bproject\b[^.]*\b(mock|interview|defend|defence|defense)\b", re.I), "project_mock"),
    (re.compile(r"pseudo[\s-]?code", re.I), "pseudocode"),
    (re.compile(r"\bresume\b|\bats\b|\bcv\b", re.I), "resume_ats"),
    (re.compile(r"\bemail\b|\bessay\b|written round|written communication", re.I), "written_round"),
    (re.compile(r"\b(interview mock|mock interview)\b", re.I), "interview_mock"),
    (re.compile(r"\baptitude\b|\bquant\b|quantitative|reasoning|verbal", re.I), "aptitude"),
    (re.compile(r"\bdsa\b|leetcode|\bcoding\b|\balgorithm", re.I), "coding"),
    (re.compile(r"\bmock\b", re.I), "skill_mock"),
]


def infer_tool_code(text: str) -> str | None:
    for pattern, code in TOOL_INTENTS:
        if pattern.search(text or ""):
            return code
    return None


def _clamp_day(value: int, lo: int, hi: int) -> int:
    return max(lo, min(hi, value))


def build_day_index(plan_root: dict[str, Any] | None) -> dict[int, dict[str, Any]]:
    phases = (plan_root or {}).get("phases")
    if not isinstance(phases, list):
        return {}

    flat: list[dict[str, Any]] = []
    week_ordinal = 0
    for phase in phases:
        for week in phase.get("weeks") or []:
            this_week = week_ordinal
            week_ordinal += 1
            for day in week.get("daily") or []:
                if not day:
                    continue
                flat.append(
                    {
                        "rawDay": int(day.get("day") or 0),
                        "weekOrdinal": this_week,
                        "theme": week.get("theme"),
                        "minutes": int(day.get("minutes") or 0),
                        "tasks": list(day.get("tasks") or []),
                        "toolHref": day.get("tool_href"),
                    }
                )
    if not flat:
        return {}

    horizon = plan_horizon_from_plan_json(plan_root)
    raws = [f["rawDay"] for f in flat if f["rawDay"]]
    week_relative = len(set(raws)) < len(raws)

    index: dict[int, dict[str, Any]] = {}
    for entry in flat:
        absolute = (
            entry["weekOrdinal"] * 7 + _clamp_day(entry["rawDay"], 1, 7)
            if week_relative
            else _clamp_day(entry["rawDay"], 1, horizon)
        )
        index[absolute] = {**entry, "day": absolute}
    return index


def tasks_for_plan_day(
    entry: dict[str, Any] | None,
    *,
    day_n: int,
    focus_pillar: str | None = None,
) -> list[dict[str, Any]]:
    if not entry:
        return []
    texts = entry.get("tasks") or []
    count = len(texts) or 1
    per_task = max(5, int((entry.get("minutes") or 20) / count))
    out: list[dict[str, Any]] = []
    for i, text in enumerate(texts):
        title = str(text or "").strip()
        tool_code = infer_tool_code(title)
        theme = entry.get("theme") or "today's theme"
        tool_slug = tool_code or "manual"
        out.append(
            {
                "task_key": f"plan-d{day_n}-{tool_slug}-{i}",
                "text": title,
                "title": title,
                "required": True,
                "minutes": per_task,
                "done": False,
                "status": "todo",
                "kind": "tool" if tool_code else "manual",
                "tool_code": tool_code,
                "tool_href": entry.get("toolHref"),
                "why_this": (
                    f"From your personalized plan — {theme}."
                    if entry.get("theme")
                    else "Picked from your personalized placement plan."
                ),
                "plan_day": day_n,
                "focus_pillar": focus_pillar,
            }
        )
    return out

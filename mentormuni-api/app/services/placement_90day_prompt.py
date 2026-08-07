"""Prompt for personalized 90-day MNC placement roadmap (post Week-1 baseline)."""

from __future__ import annotations

import json
from typing import Any


def render_placement_90day_prompt(
    analysis: dict[str, Any],
    *,
    target_companies: list[str],
    batch_year: int | None = None,
) -> str:
    companies = ", ".join(target_companies)
    year_line = (
        f"Batch / graduating year hint: {batch_year}."
        if batch_year
        else "Assume final-year (4th year) engineering student preparing for campus placements."
    )

    snapshot = {
        "overall_score": analysis.get("overall_score"),
        "scores_by_tool": analysis.get("scores_by_tool") or {},
        "top_strengths": (analysis.get("top_strengths") or [])[:12],
        "top_weaknesses": (analysis.get("top_weaknesses") or [])[:12],
        "recommendations": (analysis.get("recommendations") or [])[:12],
        "voice_avg": analysis.get("voice_avg"),
        "week_status": analysis.get("week_status"),
    }

    return f"""You are MentorMuni's placement coach for Indian engineering campus drives.

STUDENT CONTEXT
- {year_line}
- Preparing for MNC / campus placements at companies like: {companies}.
- They finished MentorMuni Week-1 baseline tools (snap, aptitude, skill readiness, skill mock, project mock, interview readiness, live mock, HR mock).
- Use ONLY the baseline analysis below to personalize the plan. Prioritize weakest areas first; protect strengths.

BASELINE ANALYSIS (JSON):
{json.dumps(snapshot, ensure_ascii=True)}

TASK
Return ONE JSON object (no markdown) for a 90-day roadmap AFTER baseline:

HARD RULES
1. phases: exactly two objects — phase_id "prep" then phase_id "mocks".
2. prep: day_start=1, day_end=42, exactly 6 weeks (prep_week 1..6). Contiguous days 1..42 each appear exactly once in daily arrays.
3. mocks: day_start=43, day_end=90. Contiguous days 43..90 each appear exactly once. AI MOCK INTERVIEWS ONLY — no theory curricula. Rotate skill_mock / project_mock / interview_mock / hr_mock. Include tool_href like "/studentportal/tools/skill_mock?from=journey" (or project_mock|interview_mock|hr_mock).
4. Each daily entry: {{ "day": <int>, "tasks": ["short task", ...], "minutes": <30-180> }}. Max 3 tasks (prefer 2). Tasks must be concrete and time-boxed. No essays.
5. Each prep week: theme, based_on_weaknesses (from analysis), focus_tools (tool_code strings), daily list.
6. Mock weeks: mock_week 1..6 for days 43-84 (7 days each), mock_week 7 for days 85-90 only.
7. title, target_role, target_companies (array), baseline_summary (2 sentences), confidence_goal (1 sentence).

OUTPUT SHAPE
{{
  "title": "90-day MNC placement roadmap",
  "target_role": "Software Engineer / Graduate hire",
  "target_companies": ["TCS", "Accenture", "Persistent", "Microsoft"],
  "baseline_summary": "...",
  "confidence_goal": "...",
  "phases": [
    {{
      "phase_id": "prep",
      "label": "Gap-driven prep",
      "day_start": 1,
      "day_end": 42,
      "weeks": [
        {{
          "prep_week": 1,
          "theme": "...",
          "based_on_weaknesses": ["..."],
          "focus_tools": ["aptitude"],
          "daily": [{{ "day": 1, "tasks": ["..."], "minutes": 90 }}]
        }}
      ]
    }},
    {{
      "phase_id": "mocks",
      "label": "AI mock interview only",
      "day_start": 43,
      "day_end": 90,
      "weeks": [
        {{
          "mock_week": 1,
          "theme": "...",
          "focus_tools": ["skill_mock", "project_mock"],
          "daily": [{{ "day": 43, "tasks": ["1x skill AI mock"], "minutes": 60, "tool_href": "/studentportal/tools/skill_mock?from=journey" }}]
        }}
      ]
    }}
  ]
}}

Return ONLY valid JSON. Every day from 1 to 90 must appear exactly once.
"""

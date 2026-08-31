"""Prompt for personalized 30–45 day placement roadmap (post assessment week)."""

from __future__ import annotations

import json
from typing import Any

from app.student_roadmap.plan_horizon import plan_horizon_days, plan_phase_layout


def render_placement_90day_prompt(
    analysis: dict[str, Any],
    *,
    target_companies: list[str],
    batch_year: int | None = None,
    student_band: str = "balanced",
    target_tier: str | None = None,
    starting_level: str | None = None,
    baseline_path: str | None = None,
    daily_budget_minutes: int | None = None,
    horizon_days: int | None = None,
) -> str:
    horizon = horizon_days or plan_horizon_days(student_band)
    layout = plan_phase_layout(horizon)
    prep_end = layout["prep_end"]
    mock_start = layout["mock_start"]
    prep_weeks = layout["prep_weeks"]
    mock_weeks = layout["mock_weeks"]

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

    template_rules = {
        "foundation": (
            "STUDENT BAND: foundation (overall < 40%). "
            "Early prep weeks must emphasize aptitude, verbal reasoning, and communication drills. "
            "Defer full AI mocks until the second half of prep. Shorter daily tasks (30–60 min)."
        ),
        "balanced": (
            "STUDENT BAND: balanced (40–84%). "
            "Gap-driven prep first, then a mock-heavy finish — weighted to their weaknesses."
        ),
        "interview_ready": (
            "STUDENT BAND: interview-ready (85%+). "
            "Short gap sweeps in prep; bias heavily toward AI mocks and company-style drills. "
            "Keep daily tasks 45–75 min."
        ),
    }.get(
        student_band,
        "STUDENT BAND: balanced. Gap-driven prep then mock-only phase.",
    )

    tier_line = (
        f"Target tier: {target_tier} (mass_recruiter weights aptitude+communication; "
        f"product weights coding+technical)."
        if target_tier
        else "Target tier: mass_recruiter (default)."
    )
    profile_line = (
        f"Starting level: {starting_level or 'some_experience'}. "
        f"Baseline path: {baseline_path or 'standard'}. "
        f"Typical daily budget: {daily_budget_minutes or 25} minutes."
    )

    return f"""You are MentorMuni's placement coach for Indian engineering campus drives.

STUDENT CONTEXT
- {year_line}
- Preparing for MNC / campus placements at companies like: {companies}.
- {tier_line}
- {profile_line}
- They finished the assessment week (8 checks: snap, aptitude, skill readiness, skill mock, project mock, interview readiness, live mock, HR mock).
- Use ONLY the assessment analysis below to personalize the plan. Prioritize weakest areas first; protect strengths.
- Every student gets a different plan — no generic copy-paste weeks.
- {template_rules}

ASSESSMENT ANALYSIS (JSON):
{json.dumps(snapshot, ensure_ascii=True)}

TASK
Return ONE JSON object (no markdown) for a {horizon}-day personalized roadmap AFTER assessment:

HARD RULES
1. phases: exactly two objects — phase_id "prep" then phase_id "mocks".
2. prep: day_start=1, day_end={prep_end}, exactly {prep_weeks} weeks (prep_week 1..{prep_weeks}). Contiguous days 1..{prep_end} each appear exactly once in daily arrays.
3. mocks: day_start={mock_start}, day_end={horizon}. Contiguous days {mock_start}..{horizon} each appear exactly once. AI MOCK INTERVIEWS ONLY — no theory curricula. Rotate skill_mock / project_mock / interview_mock / hr_mock. Include tool_href like "/studentportal/tools/skill_mock?from=journey" (or project_mock|interview_mock|hr_mock).
4. Each daily entry: {{ "day": <int>, "tasks": ["short task", ...], "minutes": <30-180> }}. Max 3 tasks (prefer 2). Tasks must be concrete and time-boxed. No essays.
5. Each prep week: theme, based_on_weaknesses (from analysis), focus_tools (tool_code strings), daily list.
6. Mock weeks: mock_week 1..{mock_weeks} covering days {mock_start}–{horizon}.
7. title, target_role, target_companies (array), baseline_summary (2 sentences on strengths/gaps), confidence_goal (1 sentence).

OUTPUT SHAPE
{{
  "title": "{horizon}-day personalized placement roadmap",
  "target_role": "Software Engineer / Graduate hire",
  "target_companies": ["TCS", "Accenture", "Persistent", "Microsoft"],
  "baseline_summary": "...",
  "confidence_goal": "...",
  "phases": [
    {{
      "phase_id": "prep",
      "label": "Gap-driven prep",
      "day_start": 1,
      "day_end": {prep_end},
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
      "day_start": {mock_start},
      "day_end": {horizon},
      "weeks": [
        {{
          "mock_week": 1,
          "theme": "...",
          "focus_tools": ["skill_mock", "project_mock"],
          "daily": [{{ "day": {mock_start}, "tasks": ["1x skill AI mock"], "minutes": 60, "tool_href": "/studentportal/tools/skill_mock?from=journey" }}]
        }}
      ]
    }}
  ]
}}

Return ONLY valid JSON. Every day from 1 to {horizon} must appear exactly once.
"""

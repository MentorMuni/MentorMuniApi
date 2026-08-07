"""Prompt for student Progress — learning topics from strengths/weaknesses."""

from __future__ import annotations

import json
from typing import Any


def render_progress_topics_prompt(analysis: dict[str, Any], *, activity: dict[str, Any] | None = None) -> str:
    snapshot = {
        "overall_score": analysis.get("overall_score"),
        "scores_by_tool": analysis.get("scores_by_tool") or {},
        "top_strengths": (analysis.get("top_strengths") or [])[:12],
        "top_weaknesses": (analysis.get("top_weaknesses") || [])[:12],
        "recommendations": (analysis.get("recommendations") || [])[:12],
        "voice_avg": analysis.get("voice_avg"),
        "week_status": analysis.get("week_status"),
    }
    activity_snap = {
        "completed_count": (activity or {}).get("completed_count"),
        "total_count": (activity or {}).get("total_count"),
        "completed_steps": (activity or {}).get("completed_steps") or [],
    }

    return f"""You are MentorMuni's placement coach for Indian engineering campus drives.

STUDENT SNAPSHOT
- They are building placement readiness on MentorMuni.
- Use ONLY the analysis and activity below. Do not invent scores.
- Prioritize weak points first, then nearby related topics that often trip the same students.
- Protect strengths: mention them briefly as keep-alive practice, not as new deep dives.

ANALYSIS (JSON):
{json.dumps(snapshot, ensure_ascii=True)}

ACTIVITY (JSON):
{json.dumps(activity_snap, ensure_ascii=True)}

TASK
Return ONE JSON object (no markdown) with learning topics in exactly three pillars:

1. aptitude — quantitative, logical, verbal, and related campus aptitude areas
2. skills — technical skills, DSA/core CS, projects, skill mocks
3. interview — interview craft, communication, HR/behavioral, live interview performance

HARD RULES
1. Each pillar must have 4–7 topics.
2. Each topic object:
   {{
     "topic": "short concrete topic name",
     "why": "1 sentence tied to their weakness or nearby gap",
     "nearby": "optional related area to study next",
     "priority": 1|2|3,
     "suggested_minutes": 30|45|60|90
   }}
3. At least half the topics in each pillar should map to listed weaknesses or low scores.
4. Include nearby areas (adjacent skills/topics) so the student does not study in a silo.
5. Keep language simple and actionable for a final-year student.
6. Also include:
   - "coach_summary": 2 sentences on where they stand
   - "focus_order": array of the three pillars ordered by urgency for this student

OUTPUT SHAPE
{{
  "coach_summary": "...",
  "focus_order": ["aptitude", "skills", "interview"],
  "learning_topics": {{
    "aptitude": [{{ "topic": "...", "why": "...", "nearby": "...", "priority": 1, "suggested_minutes": 45 }}],
    "skills": [],
    "interview": []
  }}
}}
"""

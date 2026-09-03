"""OpenAI prompts for TPO campus / HOD branch / single-student performance briefs."""

from __future__ import annotations

import json
from typing import Any, Optional

# Deep analysis model default: settings.org_performance_insight_model (gpt-4.1).

INSIGHT_SYSTEM = """
You are MentorMuni Placement Intelligence — a senior campus placement analyst who briefs
Indian college TPOs (Training & Placement Officers) and HODs (Heads of Department).

You have placed thousands of engineering students into product and service MNCs.
You read aggregate readiness metrics and turn them into decisions: who is drive-ready,
who needs coaching, what to run this week, and who to shortlist or hold.

VOICE:
- Professional Indian English. Concise. Boardroom-ready for dean / director / HR partners.
- Concrete verbs: Assign, Run, Notify, Escalate, Shortlist, Hold.
- Never call students "weak". Say less prepared / needs more practice / below drive-ready.
- Never invent departments, student names, scores, or percentages not present in the metrics JSON.
- Prefer numbers from the JSON (%, counts, pillar averages). Cite them in bullets when helpful.
- If coverage is low, say the picture is incomplete and prioritize assessment completion first.

OUTPUT:
Return STRICT JSON only — no markdown fences, no commentary outside the JSON object.
""".strip()

STUDENT_INSIGHT_SYSTEM = """
You are MentorMuni Placement Intelligence briefing a TPO or HOD about ONE student.

VOICE:
- Professional Indian English. Concise. Coaching-oriented for staff, not the student.
- Never call the student "weak". Say less prepared / needs more practice.
- Use ONLY scores, tools, and names in the metrics JSON. Do not invent assessments.
- If dept_context is present, compare fairly to branch averages; otherwise stay student-only.

OUTPUT:
Return STRICT JSON only — no markdown fences, no commentary outside the JSON object.
""".strip()

_JSON_SHAPE = """
Return STRICT JSON with this exact shape:
{
  "summary": "string",
  "going_well": ["string", "..."],
  "concerns": ["string", "..."],
  "actions": ["string", "..."],
  "shortlist_notes": ["string", "..."]
}
""".strip()


def build_campus_insight_user_prompt(
    *,
    metrics: dict[str, Any],
    max_actions: int,
    focus_label: str,
    scope_label: str,
) -> str:
    return f"""
ROLE: TPO / campus placement office — executive readiness brief for dean, director & HR partners.

AUDIENCE SCOPE: {scope_label}
FOCUS AREA: {focus_label}

YOUR JOB:
Write a decision brief from the METRICS JSON only. Cover, in order of importance:
1) Overall readiness & score coverage (is the picture trustworthy yet?)
2) Drive-ready vs developing vs less-prepared bands
3) Pillar strengths / gaps (aptitude, skills, interview, communication, voice mocks)
4) Department comparison — which branch leads / lags each pillar (if departments present)
5) Engagement (active / idle / never started) and baseline test completion
6) Shortlist vs hold guidance for upcoming drives

{_JSON_SHAPE}

FIELD RULES:
- summary: 3–5 sentences. Lead with the campus verdict, then coverage, then the one biggest risk.
- going_well: 2–4 short factual bullets with numbers when available.
- concerns: 2–4 short factual bullets (risks, gaps, inactivity, low coverage).
- actions: {max_actions} items (minimum 3). Each one imperative sentence staff can do this week
  ("Assign…", "Run…", "Notify…", "Escalate…"). Name the cohort size or % when possible.
- shortlist_notes: 1–3 bullets — who/what to shortlist now vs hold for more prep.

METRICS JSON:
{json.dumps(metrics, ensure_ascii=True)}
""".strip()


def build_branch_insight_user_prompt(
    *,
    metrics: dict[str, Any],
    max_actions: int,
    focus_label: str,
    scope_label: str,
) -> str:
    return f"""
ROLE: HOD / Placement Coordinator — deep branch research brief for mentoring your department.

AUDIENCE SCOPE: {scope_label}
FOCUS AREA: {focus_label}

YOUR JOB:
Write a branch coaching brief from the METRICS JSON only. Prioritize:
1) Branch readiness vs drive-ready bar (≥75%) and assessment coverage
2) Pillar diagnosis — which skill areas to coach this fortnight
3) Area boards — name top performers and less-prepared students when present in metrics
4) Top strengths / preparation gaps themes among scored students
5) Tool / baseline completion — who is stuck mid-roadmap
6) Concrete mentor actions (mocks, notify cohorts, assign practice) for THIS department only

Do NOT write a campus-wide dean report. Write for the HOD who will talk to students tomorrow.

{_JSON_SHAPE}

FIELD RULES:
- summary: 3–5 sentences. Branch verdict, coverage, then the primary coaching priority.
- going_well: 2–4 bullets (strengths, strong pillars, engagement wins).
- concerns: 2–4 bullets (less-prepared count, gaps, idle/never-started, incomplete checks).
- actions: {max_actions} items (minimum 3). Imperative, department-scoped, this-week feasible.
- shortlist_notes: 1–3 bullets naming students from leaders / at_risk_sample / area_boards
  when those arrays exist — shortlist vs hold. If names are missing, describe criteria only.

METRICS JSON:
{json.dumps(metrics, ensure_ascii=True)}
""".strip()


def build_student_insight_user_prompt(
    *,
    metrics: dict[str, Any],
    max_actions: int,
    focus_label: str,
) -> str:
    return f"""
ROLE: Staff coaching brief about ONE enrolled student.

FOCUS AREA: {focus_label}

YOUR JOB:
From the STUDENT METRICS JSON only, brief the TPO/HOD on:
1) Overall readiness & drive-ready verdict
2) Progress through baseline checks (done vs pending from step_status / tools)
3) Strengths to protect and gaps to coach
4) Activity / recency signals if present
5) Branch comparison only when dept_context exists

{_JSON_SHAPE}

FIELD RULES:
- summary: 3–4 sentences — readiness, check progress, drive-readiness verdict, one coaching focus.
- going_well: 2–4 short bullets (strengths, completed checks, strong pillars).
- concerns: 2–4 short bullets (gaps, pending checks, inactivity, below branch avg if given).
- actions: {max_actions} items (minimum 3). What staff should assign / escalate / follow up.
- shortlist_notes: 1–3 bullets — drive verdict + what the student should do next.

STUDENT METRICS JSON:
{json.dumps(metrics, ensure_ascii=True)}
""".strip()


def select_campus_or_branch_prompt(
    *,
    is_branch: bool,
    metrics: dict[str, Any],
    max_actions: int,
    focus_label: str,
    scope_label: str,
) -> str:
    if is_branch:
        return build_branch_insight_user_prompt(
            metrics=metrics,
            max_actions=max_actions,
            focus_label=focus_label,
            scope_label=scope_label,
        )
    return build_campus_insight_user_prompt(
        metrics=metrics,
        max_actions=max_actions,
        focus_label=focus_label,
        scope_label=scope_label,
    )


def scope_is_branch(summary_scope: str, department_id: Optional[int]) -> bool:
    """HOD / filtered dept views get the branch research prompt."""
    if summary_scope == "department":
        return True
    return department_id is not None

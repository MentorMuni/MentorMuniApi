"""OpenAI deep analysis brief for TPO/HOD performance dashboards."""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any, Optional

from openai import AsyncOpenAI

from app.core.config import settings
from app.org_performance.schemas import InsightOut, InsightPayload, InsightRequest, PerformanceSummaryOut

logger = logging.getLogger(__name__)

CAMPUS_INSIGHT_PROMPT = r"""
You are Mentor Muni — placement analytics advisor for Indian college TPOs and HODs.

Given ONLY the metrics JSON below, write a decision brief with full clarity for deep student prep understanding.

Rules:
- Use ONLY the provided numbers. Do not invent departments, students, or scores.
- Cover readiness bands, test completion (given vs remaining), pillar strengths and preparation gaps,
  top performers vs less-prepared students, and shortlist readiness when present.
- Never call students "weak". Say they are less prepared / need more practice.
- Be concrete and actionable for campus placement prep (aptitude, skills, interview mocks, shortlisting).
- Tone: professional Indian English, concise, respectful.
- Return STRICT JSON only:
{
  "summary": "3-5 sentences: how things are going, test progress, who is ready vs less prepared",
  "going_well": ["bullet", "bullet"],
  "concerns": ["bullet", "bullet"],
  "actions": ["action 1", "action 2", "action 3"],
  "shortlist_notes": ["who/what to shortlist or hold for more prep", "bullet"]
}
- going_well / concerns: 2 to 4 short factual bullets each.
- actions: 3 to MAX_ACTIONS items, each one sentence, imperative ("Assign…", "Run…", "Notify…").
- shortlist_notes: 1 to 3 bullets for drive shortlisting / hold decisions.
FOCUS_AREA: FOCUS_LABEL

Audience scope: SCOPE_LABEL

METRICS:
"""


async def generate_insight(
    summary: PerformanceSummaryOut,
    body: InsightRequest,
    *,
    force_heuristic: bool = False,
) -> InsightOut:
    metrics = _metrics_for_llm(
        summary,
        include_leaderboard=body.include_leaderboard,
        focus_area=body.focus_area,
    )
    scope_label = (
        "Campus-wide TPO view"
        if summary.scope == "organization" and summary.department_id is None
        else (
            "TPO filtered department view"
            if summary.scope == "organization"
            else "Single department HOD view"
        )
    )
    focus_label = body.focus_area or "overall (all areas)"
    generated_at = datetime.now(timezone.utc).isoformat()
    heuristic = _heuristic_insight(summary, body.max_actions, focus_area=body.focus_area)

    if force_heuristic or not (settings.openai_api_key or "").strip():
        return InsightOut(
            ok=True,
            source="heuristic",
            model=None,
            generated_at=generated_at,
            organization_id=summary.organization_id,
            department_id=summary.department_id,
            scope=summary.scope,
            metrics=metrics,
            insight=heuristic,
        )

    prompt = (
        CAMPUS_INSIGHT_PROMPT.replace("MAX_ACTIONS", str(body.max_actions))
        .replace("SCOPE_LABEL", scope_label)
        .replace("FOCUS_LABEL", focus_label)
        + json.dumps(metrics, ensure_ascii=True)
    )
    model = settings.org_performance_insight_model
    try:
        client = AsyncOpenAI(api_key=settings.openai_api_key)
        resp = await client.chat.completions.create(
            model=model,
            messages=[
                {
                    "role": "system",
                    "content": "Return only valid JSON for campus placement analytics briefs.",
                },
                {"role": "user", "content": prompt},
            ],
            temperature=0.3,
            max_tokens=1100,
            response_format={"type": "json_object"},
        )
        content = (resp.choices[0].message.content or "").strip()
        payload = _parse_insight(content, body.max_actions, fallback=heuristic)
        return InsightOut(
            ok=True,
            source="openai",
            model=model,
            generated_at=generated_at,
            organization_id=summary.organization_id,
            department_id=summary.department_id,
            scope=summary.scope,
            metrics=metrics,
            insight=payload,
        )
    except Exception:
        logger.exception("org performance insight failed")
        return InsightOut(
            ok=True,
            source="heuristic",
            model=None,
            generated_at=generated_at,
            organization_id=summary.organization_id,
            department_id=summary.department_id,
            scope=summary.scope,
            metrics=metrics,
            insight=heuristic,
        )


def _metrics_for_llm(
    summary: PerformanceSummaryOut,
    *,
    include_leaderboard: bool,
    focus_area: Optional[str] = None,
) -> dict[str, Any]:
    data = {
        "scope": summary.scope,
        "department_id": summary.department_id,
        "focus_area": focus_area or "overall",
        "students_total": summary.students_total,
        "students_scored": summary.students_scored,
        "coverage_pct": summary.coverage_pct,
        "drive_ready_pct": summary.drive_ready_pct,
        "drive_ready_of_scored_pct": summary.drive_ready_of_scored_pct,
        "avg_readiness": summary.avg_readiness,
        "avg_mock": summary.avg_mock,
        "bands": summary.bands.model_dump(),
        "pillars": summary.pillars.model_dump(),
        "tests": summary.tests.model_dump(),
        "level_funnel": [x.model_dump() for x in summary.level_funnel],
        "tool_coverage": [t.model_dump() for t in summary.tool_coverage],
        "clarity": summary.clarity.model_dump(),
        "top_gaps": [g.model_dump() for g in summary.top_gaps[:6]],
        "top_strengths": [s.model_dump() for s in summary.top_strengths[:6]],
        "active_7d": summary.active_7d,
        "idle_count": summary.idle_count,
        "inactive_14d": summary.inactive_14d,
        "never_started": summary.never_started,
        "pending_invites": summary.pending_invites,
        "upcoming_drives": summary.upcoming_drives,
        "hod_gaps": summary.hod_gaps,
        "departments": [
            {
                "code": d.code,
                "name": d.name,
                "students": d.students,
                "coverage_pct": d.coverage_pct,
                "avg_readiness": d.avg_readiness,
                "avg_tests_done": d.avg_tests_done,
                "strong": d.strong,
                "mid": d.mid,
                "weak": d.weak,
                "never_started": d.never_started,
                "top_gap": d.top_gap,
                "hod_status": d.hod_status,
            }
            for d in summary.by_department
        ],
        "area_boards": [
            {
                "area": b.area,
                "label": b.label,
                "avg_score": b.avg_score,
                "students_scored": b.students_scored,
                "top": [
                    {"rank": t.rank, "name": t.name, "score": t.score, "dept": t.department_name}
                    for t in b.top[:5]
                ],
                "less_prepared": [
                    {"rank": t.rank, "name": t.name, "score": t.score, "dept": t.department_name}
                    for t in b.less_prepared[:5]
                ],
            }
            for b in summary.area_boards
            if not focus_area or focus_area == "overall" or b.area == focus_area
        ],
        "at_risk_count": len(summary.at_risk),
    }
    if include_leaderboard:
        data["leaders"] = [
            {
                "name": l.name,
                "department": l.department_name,
                "readiness": l.readiness,
                "best_area": l.best_area,
                "tests_done": l.tests_done,
            }
            for l in summary.leaders[:5]
        ]
        data["at_risk_sample"] = [
            {"name": l.name, "readiness": l.readiness, "weakness": l.weakness}
            for l in summary.at_risk[:5]
        ]
    return data


def _parse_insight(
    content: str, max_actions: int, *, fallback: Optional[InsightPayload] = None
) -> InsightPayload:
    fb = fallback or InsightPayload(
        summary="Campus performance brief is temporarily unavailable. Review readiness bands and less-prepared students.",
        going_well=[],
        concerns=[],
        actions=[
            "Review students below 50% readiness",
            "Assign aptitude or skill mocks to developing cohorts",
            "Follow up with inactive students this week",
        ],
        shortlist_notes=[],
    )
    try:
        data = json.loads(content)
    except json.JSONDecodeError:
        return fb
    summary = str(data.get("summary") or "").strip() or fb.summary
    actions_raw = data.get("actions") if isinstance(data.get("actions"), list) else []
    actions = [str(a).strip() for a in actions_raw if str(a).strip()][:max_actions]
    while len(actions) < 3:
        actions.append("Review department readiness gaps and assign a targeted practice block.")

    def _bullets(key: str, fallback_list: list[str], limit: int = 4) -> list[str]:
        raw = data.get(key) if isinstance(data.get(key), list) else []
        out = [str(x).strip() for x in raw if str(x).strip()][:limit]
        return out or fallback_list

    return InsightPayload(
        summary=summary[:1400],
        going_well=_bullets("going_well", fb.going_well),
        concerns=_bullets("concerns", fb.concerns),
        actions=actions,
        shortlist_notes=_bullets("shortlist_notes", fb.shortlist_notes, 3),
    )


def _heuristic_insight(
    summary: PerformanceSummaryOut,
    max_actions: int,
    *,
    focus_area: Optional[str] = None,
) -> InsightPayload:
    clarity = summary.clarity
    avg = summary.avg_readiness
    weak = summary.bands.weak
    gap = summary.top_gaps[0].label if summary.top_gaps else "core fundamentals"
    strength = summary.top_strengths[0].label if summary.top_strengths else "communication basics"
    scope = "Campus" if summary.scope == "organization" and not summary.department_id else "Branch"
    tests = summary.tests
    focus = focus_area or "overall"
    board = next((b for b in summary.area_boards if b.area == focus), None)
    if board is None:
        board = next((b for b in summary.area_boards if b.area == "overall"), None)

    summary_text = (
        f"{scope} avg readiness is {avg if avg is not None else 'n/a'}% with "
        f"{summary.coverage_pct}% score coverage ({summary.students_scored}/{summary.students_total}). "
        f"Students average {tests.avg_tests_done}/{tests.tools_total} tests done "
        f"({tests.students_none_done} none started, {tests.students_all_done} completed all). "
        f"{summary.drive_ready_of_scored_pct}% of scored are drive-ready; "
        f"{weak} are less prepared (<50%). "
        f"Top prep gap: {gap}. Strength: {strength}."
    )
    actions = list(clarity.priorities) if clarity.priorities else [
        f"Assign targeted practice for the {weak} less-prepared students (focus: {gap})",
        "Run a skills or interview mock sprint for the developing band (50–74%)",
        "Message students with remaining baseline tests to resume the next unlocked step",
    ]
    shortlist_notes: list[str] = []
    if board and board.top:
        names = ", ".join(t.name for t in board.top[:3])
        shortlist_notes.append(
            f"Shortlist candidates ({board.label}): {names}"
            + (f" (avg {board.avg_score}%)" if board.avg_score is not None else "")
        )
    if board and board.less_prepared:
        names = ", ".join(t.name for t in board.less_prepared[:3])
        shortlist_notes.append(
            f"Hold for more prep before shortlist ({board.label}): {names}"
        )
    if not shortlist_notes:
        shortlist_notes.append("Build shortlist after more students complete aptitude + skill mocks.")

    return InsightPayload(
        summary=summary_text,
        going_well=list(clarity.going_well),
        concerns=list(clarity.concerns),
        actions=actions[:max_actions],
        shortlist_notes=shortlist_notes[:3],
    )

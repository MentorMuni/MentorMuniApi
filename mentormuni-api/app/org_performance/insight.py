"""OpenAI deep analysis brief for TPO/HOD performance dashboards."""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any, Optional

from openai import AsyncOpenAI

from app.core.config import settings
from app.org_performance.prompt import (
    INSIGHT_SYSTEM,
    STUDENT_INSIGHT_SYSTEM,
    build_student_insight_user_prompt,
    scope_is_branch,
    select_campus_or_branch_prompt,
)
from app.org_performance.schemas import (
    DeptPerformanceRow,
    InsightOut,
    InsightPayload,
    InsightRequest,
    PerformanceSummaryOut,
    StudentInsightOut,
    StudentInsightRequest,
    StudentScorecard,
)
from app.student_roadmap.constants import TOOL_META

logger = logging.getLogger(__name__)

# Deep placement briefs — enough room for structured JSON with named actions.
_INSIGHT_MAX_TOKENS = 1600
_STUDENT_INSIGHT_MAX_TOKENS = 1200
_INSIGHT_TEMPERATURE = 0.25


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

    is_branch = scope_is_branch(summary.scope, summary.department_id)
    prompt = select_campus_or_branch_prompt(
        is_branch=is_branch,
        metrics=metrics,
        max_actions=body.max_actions,
        focus_label=focus_label,
        scope_label=scope_label,
    )
    model = (settings.org_performance_insight_model or "gpt-4.1").strip() or "gpt-4.1"
    try:
        client = AsyncOpenAI(api_key=settings.openai_api_key)
        resp = await client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": INSIGHT_SYSTEM},
                {"role": "user", "content": prompt},
            ],
            temperature=_INSIGHT_TEMPERATURE,
            max_tokens=_INSIGHT_MAX_TOKENS,
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
                "pillars": d.pillars.model_dump(),
                "best_pillar": d.best_pillar,
                "weakest_pillar": d.weakest_pillar,
                "strong": d.strong,
                "mid": d.mid,
                "weak": d.weak,
                "never_started": d.never_started,
                "top_gap": d.top_gap,
                "hod_status": d.hod_status,
            }
            for d in summary.by_department
        ],
        "branch_pillar_rankings": summary.branch_pillar_rankings.model_dump(),
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


async def generate_student_insight(
    card: StudentScorecard,
    body: StudentInsightRequest,
    *,
    organization_id: int,
    scope: str,
    dept_context: Optional[DeptPerformanceRow] = None,
    force_heuristic: bool = False,
) -> StudentInsightOut:
    metrics = _student_metrics_for_llm(card, dept_context=dept_context, focus_area=body.focus_area)
    focus_label = body.focus_area or "overall (all areas)"
    generated_at = datetime.now(timezone.utc).isoformat()
    heuristic = _heuristic_student_insight(card, body.max_actions, dept_context=dept_context)

    if force_heuristic or not (settings.openai_api_key or "").strip():
        return StudentInsightOut(
            ok=True,
            source="heuristic",
            model=None,
            generated_at=generated_at,
            organization_id=organization_id,
            student_id=card.id,
            student_name=card.name,
            department_id=card.department_id,
            department_name=card.department_name,
            scope=scope,  # type: ignore[arg-type]
            metrics=metrics,
            insight=heuristic,
        )

    prompt = build_student_insight_user_prompt(
        metrics=metrics,
        max_actions=body.max_actions,
        focus_label=focus_label,
    )
    model = (settings.org_performance_insight_model or "gpt-4.1").strip() or "gpt-4.1"
    try:
        client = AsyncOpenAI(api_key=settings.openai_api_key)
        resp = await client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": STUDENT_INSIGHT_SYSTEM},
                {"role": "user", "content": prompt},
            ],
            temperature=_INSIGHT_TEMPERATURE,
            max_tokens=_STUDENT_INSIGHT_MAX_TOKENS,
            response_format={"type": "json_object"},
        )
        content = (resp.choices[0].message.content or "").strip()
        payload = _parse_insight(content, body.max_actions, fallback=heuristic)
        return StudentInsightOut(
            ok=True,
            source="openai",
            model=model,
            generated_at=generated_at,
            organization_id=organization_id,
            student_id=card.id,
            student_name=card.name,
            department_id=card.department_id,
            department_name=card.department_name,
            scope=scope,  # type: ignore[arg-type]
            metrics=metrics,
            insight=payload,
        )
    except Exception:
        logger.exception("student insight failed for student_id=%s", card.id)
        return StudentInsightOut(
            ok=True,
            source="heuristic",
            model=None,
            generated_at=generated_at,
            organization_id=organization_id,
            student_id=card.id,
            student_name=card.name,
            department_id=card.department_id,
            department_name=card.department_name,
            scope=scope,  # type: ignore[arg-type]
            metrics=metrics,
            insight=heuristic,
        )


def _student_metrics_for_llm(
    card: StudentScorecard,
    *,
    dept_context: Optional[DeptPerformanceRow] = None,
    focus_area: Optional[str] = None,
) -> dict[str, Any]:
    tools: list[dict[str, Any]] = []
    for tool_code, status in card.step_status_by_tool.items():
        meta = TOOL_META.get(tool_code) or {}
        tools.append(
            {
                "tool": tool_code,
                "label": meta.get("title") or tool_code,
                "status": status,
                "score": card.scores_by_tool.get(tool_code),
            }
        )
    tools.sort(key=lambda t: int((TOOL_META.get(t["tool"]) or {}).get("order") or 0))

    data: dict[str, Any] = {
        "focus_area": focus_area or "overall",
        "student": {
            "id": card.id,
            "name": card.name,
            "department": card.department_name,
            "readiness": card.readiness,
            "mock_score": card.mock_score,
            "technical_score": card.technical_score,
            "communication_score": card.communication_score,
            "shortlist_score": card.shortlist_score,
            "best_area": card.best_area,
            "strength": card.strength,
            "weakness": card.weakness,
            "strengths": card.strengths[:8],
            "weaknesses": card.weaknesses[:8],
            "tests_done": card.tests_done,
            "tests_in_progress": card.tests_in_progress,
            "tests_remaining": card.tests_remaining,
            "progress_level": card.progress_level,
            "progress_pct": card.progress_pct,
            "week_status": card.week_status,
            "activity_status": card.activity_status,
            "days_inactive": card.days_inactive,
            "last_active_at": card.last_active_at,
            "scores_by_tool": card.scores_by_tool,
            "tools": tools,
        },
    }
    if dept_context is not None:
        data["dept_context"] = {
            "name": dept_context.name,
            "avg_readiness": dept_context.avg_readiness,
            "coverage_pct": dept_context.coverage_pct,
            "pillars": dept_context.pillars.model_dump(),
            "best_pillar": dept_context.best_pillar,
            "weakest_pillar": dept_context.weakest_pillar,
            "strong": dept_context.strong,
            "mid": dept_context.mid,
            "weak": dept_context.weak,
            "top_gap": dept_context.top_gap,
        }
    return data


def _heuristic_student_insight(
    card: StudentScorecard,
    max_actions: int,
    *,
    dept_context: Optional[DeptPerformanceRow] = None,
) -> InsightPayload:
    readiness = card.readiness
    name = card.name
    gap = card.weakness or (card.weaknesses[0] if card.weaknesses else "core fundamentals")
    strength = card.strength or (card.strengths[0] if card.strengths else "baseline progress")
    going_well: list[str] = []
    concerns: list[str] = []
    actions: list[str] = []
    shortlist_notes: list[str] = []

    if readiness is not None and readiness >= 75:
        going_well.append(f"{name} is drive-ready at {readiness}% overall readiness.")
    elif readiness is not None and readiness >= 50:
        going_well.append(f"{name} is in the developing band at {readiness}% readiness.")
    if card.tests_done > 0:
        going_well.append(f"Completed {card.tests_done}/8 assessment checks.")
    if strength:
        going_well.append(f"Strongest signal: {strength}.")
    if card.activity_status == "active":
        going_well.append("Active in the last 7 days.")

    if card.tests_remaining > 0:
        concerns.append(f"{card.tests_remaining} baseline check(s) still pending.")
    if readiness is not None and readiness < 50:
        concerns.append(f"Overall readiness is {readiness}% — needs focused practice before drives.")
    if card.activity_status in ("inactive", "never"):
        label = "never started" if card.activity_status == "never" else f"inactive {card.days_inactive or 14}+ days"
        concerns.append(f"Student has {label} — re-engagement needed.")
    if gap:
        concerns.append(f"Top prep gap: {gap}.")

    if card.tests_remaining > 0:
        actions.append("Message student to complete the next unlocked baseline check this week.")
    if gap:
        actions.append(f"Assign targeted practice for {gap}.")
    if readiness is not None and readiness < 75:
        actions.append("Schedule a skill or interview mock before campus shortlisting.")
    if not actions:
        actions.append("Keep weekly mock practice and track readiness before upcoming drives.")

    if readiness is not None and readiness >= 75:
        shortlist_notes.append("Drive-ready — consider for shortlist after one more mock refresh.")
    elif readiness is not None and readiness >= 50:
        shortlist_notes.append("Developing — hold shortlist until mock scores cross 75%.")
    else:
        shortlist_notes.append("Hold shortlist — complete baseline week and close top gaps first.")
    if card.tests_remaining > 0:
        shortlist_notes.append(f"Student should finish {card.tests_remaining} remaining assessment check(s).")

    if dept_context and readiness is not None and dept_context.avg_readiness is not None:
        delta = round(readiness - float(dept_context.avg_readiness), 1)
        if delta >= 5:
            going_well.append(f"Above branch average ({dept_context.avg_readiness}%) by {delta} pts.")
        elif delta <= -5:
            concerns.append(f"Below branch average ({dept_context.avg_readiness}%) by {abs(delta)} pts.")

    summary = (
        f"{name} ({card.department_name or 'no branch'}) — "
        f"readiness {readiness if readiness is not None else 'n/a'}%, "
        f"{card.tests_done}/8 checks done"
        + (f", activity: {card.activity_status}" if card.activity_status else "")
        + "."
    )

    if not going_well:
        going_well.append("Student is on the roadmap — encourage completion of baseline checks.")
    if not concerns:
        concerns.append("No critical red flags — keep monitoring mock scores and activity.")

    return InsightPayload(
        summary=summary,
        going_well=going_well[:4],
        concerns=concerns[:4],
        actions=actions[:max_actions],
        shortlist_notes=shortlist_notes[:3],
    )

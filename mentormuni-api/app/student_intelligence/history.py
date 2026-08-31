"""Readiness snapshot history + cumulative performance insights."""

from __future__ import annotations

from collections import Counter
from datetime import date, datetime, timedelta
from typing import Any
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.student_intelligence.models import StudentMemoryFact, StudentReadinessSnapshot
from app.student_intelligence.readiness import PILLAR_LABELS, PILLARS
from app.student_intelligence.schemas import ReadinessHistoryOut, ReadinessHistoryPoint


def _campus_today() -> date:
    return datetime.now(ZoneInfo("Asia/Kolkata")).date()


def _is_demo_snapshot(pillars: dict[str, Any] | None) -> bool:
    if not isinstance(pillars, dict):
        return False
    return bool(pillars.get("_demo_seed"))


async def get_readiness_history(
    db: AsyncSession,
    *,
    student_id: int,
    days: int = 30,
    anchor_date: date | None = None,
) -> ReadinessHistoryOut:
    window = max(2, min(days, 90))
    today = anchor_date or _campus_today()
    since = today - timedelta(days=window - 1)
    rows = (
        await db.execute(
            select(StudentReadinessSnapshot)
            .where(StudentReadinessSnapshot.student_id == student_id)
            .where(StudentReadinessSnapshot.snapshot_date >= since)
            .order_by(StudentReadinessSnapshot.snapshot_date.asc())
        )
    ).scalars().all()

    points = []
    for row in rows:
        # Skip seeded demo history so trends reflect real practice only
        if _is_demo_snapshot(row.pillars if isinstance(row.pillars, dict) else None):
            continue
        points.append(
            ReadinessHistoryPoint(
                date=row.snapshot_date.isoformat(),
                overall=row.overall,
                coverage=float(row.coverage) if row.coverage is not None else None,
                measured_pillars=row.measured_pillars,
                weakest_pillar=row.weakest_pillar,
                pillars=_pillar_scores_from_snapshot(row.pillars or {}),
            )
        )
    return ReadinessHistoryOut(student_id=student_id, days=window, points=points)


def _pillar_scores_from_snapshot(pillars: dict[str, Any]) -> dict[str, float | None]:
    out: dict[str, float | None] = {}
    for key in PILLARS:
        value = pillars.get(key)
        if isinstance(value, dict):
            score = value.get("score")
            if value.get("hasData") and score is not None:
                out[key] = float(score)
            else:
                out[key] = None
        elif isinstance(value, (int, float)):
            out[key] = float(value)
        else:
            out[key] = None
    return out


def _collect_topics(items: list[Any] | None, counter: Counter[str]) -> None:
    for item in items or []:
        if isinstance(item, str) and item.strip():
            counter[item.strip()] += 1
        elif isinstance(item, dict):
            text = item.get("topic") or item.get("text") or item.get("label")
            if isinstance(text, str) and text.strip():
                counter[text.strip()] += 1


async def build_cumulative_analysis(
    db: AsyncSession,
    *,
    student_id: int,
    baseline_analysis: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Merge Week-1 baseline + all assessment retakes + live memory facts.

    This keeps strengths/weaknesses evolving as the student practices beyond Week-1.
    """
    from app.student_roadmap.models import StudentAssessmentResult

    strength_counter: Counter[str] = Counter()
    weakness_counter: Counter[str] = Counter()
    sources: list[str] = []

    baseline = baseline_analysis or {}
    for s in baseline.get("top_strengths") or []:
        if isinstance(s, str) and s.strip():
            strength_counter[s.strip()] += 2  # baseline weights slightly higher
    for w in baseline.get("top_weaknesses") or []:
        if isinstance(w, str) and w.strip():
            weakness_counter[w.strip()] += 2
    if baseline.get("top_strengths") or baseline.get("top_weaknesses"):
        sources.append("baseline")

    results = (
        await db.execute(
            select(StudentAssessmentResult)
            .where(StudentAssessmentResult.user_id == student_id)
            .order_by(StudentAssessmentResult.created_at.desc())
            .limit(200)
        )
    ).scalars().all()
    if results:
        sources.append("assessments")
        for row in results:
            weight = 1
            _collect_topics(row.strengths_json, strength_counter)
            # Boost weakness counts so practice gaps stay visible
            for item in row.weaknesses_json or []:
                if isinstance(item, str) and item.strip():
                    weakness_counter[item.strip()] += weight
                elif isinstance(item, dict):
                    text = item.get("topic") or item.get("text") or item.get("label")
                    if isinstance(text, str) and text.strip():
                        weakness_counter[text.strip()] += weight

    facts = (
        await db.execute(
            select(StudentMemoryFact).where(
                StudentMemoryFact.student_id == student_id,
                StudentMemoryFact.resolved_at.is_(None),
                StudentMemoryFact.fact_type.in_(("strength", "weakness")),
            )
        )
    ).scalars().all()
    if facts:
        sources.append("memory")
        for fact in facts:
            text = (fact.fact or "").strip()
            if not text:
                continue
            if fact.fact_type == "strength":
                strength_counter[text] += 1
            elif fact.fact_type == "weakness":
                weakness_counter[text] += 1

    return {
        "top_strengths": [k for k, _ in strength_counter.most_common(10)],
        "top_weaknesses": [k for k, _ in weakness_counter.most_common(10)],
        "recommendations": list(baseline.get("recommendations") or [])[:12],
        "source": "cumulative" if sources else "baseline",
        "updated_from": sources or ["baseline"],
    }


def build_performance_insights(
    readiness: dict[str, Any],
    analysis: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Derive strong/weak pillar cards + topic lists for the student dashboard."""
    pillars = readiness.get("pillars") or {}
    measured = [
        (key, pillars[key])
        for key in PILLARS
        if isinstance(pillars.get(key), dict) and pillars[key].get("hasData")
    ]
    measured.sort(key=lambda item: item[1].get("score") or 0, reverse=True)

    strong_pillars = []
    for key, data in measured[:3]:
        score = data.get("score") or 0
        if score >= 60:
            strong_pillars.append(_pillar_card(key, data))

    strong_keys = {p["key"] for p in strong_pillars}
    weak_pillars = []
    for key, data in reversed(measured):
        if key in strong_keys and key != readiness.get("weakest_pillar"):
            continue
        score = data.get("score") or 0
        if score < 70 or key == readiness.get("weakest_pillar"):
            weak_pillars.append(_pillar_card(key, data))
        if len(weak_pillars) >= 3:
            break

    analysis = analysis or {}
    strengths = list(analysis.get("top_strengths") or [])[:6]
    weaknesses = list(analysis.get("top_weaknesses") or [])[:6]

    # Fallback: when no topic labels yet, surface live pillar names so UI isn't empty
    if not strengths:
        strengths = [
            PILLAR_LABELS.get(p["key"], p["label"])
            for p in strong_pillars
        ][:6]
    if not weaknesses:
        weaknesses = [
            PILLAR_LABELS.get(p["key"], p["label"])
            for p in weak_pillars
        ][:6]

    return {
        "focus_pillar": readiness.get("focus_pillar"),
        "weakest_pillar": readiness.get("weakest_pillar"),
        "top_strengths": strengths,
        "top_weaknesses": weaknesses,
        "strong_pillars": strong_pillars,
        "weak_pillars": weak_pillars,
        "source": analysis.get("source") or "cumulative",
        "updated_from": list(analysis.get("updated_from") or []),
    }


def _pillar_card(key: str, data: dict[str, Any]) -> dict[str, Any]:
    trend = data.get("trend")
    return {
        "key": key,
        "label": data.get("label") or key.replace("_", " ").title(),
        "score": data.get("score"),
        "trend": trend,
        "attempts": data.get("attempts") or 0,
        "confidence": data.get("confidence"),
        "hasData": bool(data.get("hasData")),
        "has_data": bool(data.get("hasData")),
        "tip": _pillar_tip(key, data.get("score"), trend),
    }


def _pillar_tip(key: str, score: int | None, trend: int | None) -> str:
    if score is None:
        return "Complete the baseline check for this area."
    if score < 50:
        return "Priority focus — schedule a short practice block this week."
    if trend is not None and trend > 0:
        return f"Improving (+{trend} since last attempt). Keep the momentum."
    if trend is not None and trend < 0:
        return "Slight dip — retry one mock to recover."
    if score >= 75:
        return "Strong area — maintain with occasional refreshers."
    return "Steady progress — one more focused session will help."


def _gate_sort_key(gate: dict[str, Any]) -> tuple[int, int]:
    """Closer gates first (smallest overall gap)."""
    if gate.get("cleared"):
        return (0, 0)
    binding = gate.get("binding_constraint") or {}
    if binding.get("pillar") == "overall":
        have = binding.get("have") or 0
        need = binding.get("need") or 0
        return (1, max(0, need - have))
    gap = binding.get("gap")
    if gap is not None:
        return (1, int(gap))
    if binding.get("unmeasured"):
        return (2, 100)
    return (2, 50)


def build_gates_summary(gates: list[dict[str, Any]] | None) -> dict[str, Any]:
    items = list(gates or [])
    cleared = [g for g in items if g.get("cleared")]
    blocked = sorted([g for g in items if not g.get("cleared")], key=_gate_sort_key)
    return {
        "cleared_count": len(cleared),
        "total_count": len(items),
        "cleared": cleared[:6],
        "next_targets": blocked[:6],
    }


def build_daily_mission_summary(daily: dict[str, Any] | None) -> dict[str, Any]:
    daily = daily or {}
    tasks = list(daily.get("tasks") or [])
    done = int(daily.get("doneCount") or sum(1 for t in tasks if t.get("done") or t.get("status") == "done"))
    total = int(daily.get("requiredCount") or len(tasks))
    current = next(
        (t for t in tasks if not t.get("done") and t.get("status") != "done"),
        None,
    )
    mode = daily.get("mode") or "baseline"
    titles = {
        "baseline": "Finish your Week-1 baseline",
        "awaiting_plan": "Generate your placement plan",
        "plan": "Today's placement mission",
        "intelligence": (
            "Practice focus — no plan tasks for today"
            if daily.get("plan_day_empty") or daily.get("fallback_reason")
            else "Today's practice focus"
        ),
    }
    title = titles.get(mode, "Today's practice")
    theme = daily.get("theme")
    day_n = daily.get("day_in_plan")
    week_ordinal = daily.get("week_ordinal")
    if mode in ("plan", "intelligence") and day_n:
        week_label = f"Week {(week_ordinal or 0) + 1}" if week_ordinal is not None else None
        parts = [p for p in [week_label, theme, f"Day {day_n}"] if p]
        if parts:
            title = " · ".join(parts)
        if mode == "intelligence" and (daily.get("plan_day_empty") or daily.get("fallback_reason")):
            title = f"{title} · off-plan practice" if parts else title

    current_task = None
    if current:
        current_task = {
            "text": current.get("text") or current.get("title"),
            "title": current.get("title") or current.get("text"),
            "href": current.get("tool_href") or current.get("href"),
            "tool_code": current.get("tool_code"),
            "action": current.get("action"),
            "task_key": current.get("task_key"),
        }
    return {
        "mode": mode,
        "title": title,
        "focus_pillar": daily.get("focus_pillar"),
        "tasks_total": total,
        "tasks_done": done,
        "current_task": current_task,
        "day_in_plan": day_n,
        "theme": theme,
        "week_ordinal": week_ordinal,
        "horizon": daily.get("horizon") or daily.get("plan_horizon"),
        "plan_id": daily.get("plan_id"),
        "fallback_reason": daily.get("fallback_reason"),
        "plan_day_empty": bool(daily.get("plan_day_empty")),
    }


def build_plan_progress(daily: dict[str, Any] | None, mission_summary: dict[str, Any] | None = None) -> dict[str, Any]:
    """Compact plan-progress payload for the dashboard quest panel."""
    daily = daily or {}
    summary = mission_summary or build_daily_mission_summary(daily)
    mode = summary.get("mode") or daily.get("mode") or "baseline"
    return {
        "mode": mode,
        "day_in_plan": summary.get("day_in_plan") or daily.get("day_in_plan"),
        "horizon": summary.get("horizon") or daily.get("horizon") or daily.get("plan_horizon"),
        "week_ordinal": summary.get("week_ordinal") if summary.get("week_ordinal") is not None else daily.get("week_ordinal"),
        "theme": summary.get("theme") or daily.get("theme"),
        "tasks_done": summary.get("tasks_done") or 0,
        "tasks_total": summary.get("tasks_total") or 0,
        "title": summary.get("title") or "",
        "plan_id": summary.get("plan_id") if summary.get("plan_id") is not None else daily.get("plan_id"),
        "fallback_reason": summary.get("fallback_reason") or daily.get("fallback_reason"),
        "plan_day_empty": bool(
            summary.get("plan_day_empty")
            if summary.get("plan_day_empty") is not None
            else daily.get("plan_day_empty")
        ),
    }

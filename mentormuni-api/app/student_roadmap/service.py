"""Student Week-1 roadmap service: seed, complete, analysis, generate 90-day plan."""

from __future__ import annotations

import logging
from collections import Counter
from datetime import datetime, timezone
from typing import Any, Optional

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.enums import RoleCode
from app.models.user import User
from app.student_roadmap.constants import (
    PLAN_GENERATING_STALE_SECONDS,
    PLAN_STATUS_FAILED,
    PLAN_STATUS_GENERATING,
    PLAN_STATUS_READY,
    PLAN_STATUS_SUPERSEDED,
    PROMPT_VERSION,
    STEP_STATUS_CURRENT,
    STEP_STATUS_DONE,
    STEP_STATUS_LOCKED,
    TOOL_CODES,
    TOOL_META,
    WEEK1_NUMBER,
    WEEK1_STEPS,
    WEEK_STATUS_DONE,
    WEEK_STATUS_IN_PROGRESS,
    DEFAULT_TARGET_COMPANIES,
)
from app.student_roadmap.models import (
    StudentAssessmentResult,
    StudentGeneratedRoadmap,
    StudentRoadmapStep,
    StudentRoadmapWeek,
)
from app.student_roadmap.normalize import normalize_complete_payload
from app.student_roadmap.schemas import (
    AnalysisOut,
    AssessmentResultOut,
    CompleteStepRequest,
    GeneratedPlanOut,
    LearningTopicOut,
    ProgressActivityOut,
    ProgressActivityStepOut,
    ProgressLearningTopicsOut,
    ProgressOut,
    RoadmapOut,
    RoadmapStepOut,
)
from app.student_roadmap.validate_plan import PlanValidationError, validate_placement_90day_plan

logger = logging.getLogger("student_roadmap")


def _iso(dt: Optional[datetime]) -> Optional[str]:
    if dt is None:
        return None
    return dt.astimezone(timezone.utc).isoformat()


def _ensure_student(user: User) -> None:
    code = user.role.role_code if user.role else None
    if code != RoleCode.STUDENT.value:
        raise HTTPException(status_code=403, detail="Student role required.")


async def _load_week(db: AsyncSession, user_id: int) -> Optional[StudentRoadmapWeek]:
    result = await db.execute(
        select(StudentRoadmapWeek)
        .where(StudentRoadmapWeek.user_id == user_id)
        .where(StudentRoadmapWeek.week_number == WEEK1_NUMBER)
        .options(selectinload(StudentRoadmapWeek.steps))
    )
    return result.scalar_one_or_none()


async def _seed_week(db: AsyncSession, user_id: int) -> StudentRoadmapWeek:
    week = StudentRoadmapWeek(
        user_id=user_id,
        week_number=WEEK1_NUMBER,
        status=WEEK_STATUS_IN_PROGRESS,
    )
    db.add(week)
    await db.flush()
    for meta in WEEK1_STEPS:
        db.add(
            StudentRoadmapStep(
                week_id=week.id,
                tool_code=meta["tool_code"],
                step_order=meta["order"],
                status=STEP_STATUS_CURRENT if meta["order"] == 1 else STEP_STATUS_LOCKED,
                strengths_json=[],
                weaknesses_json=[],
                recommendations_json=[],
            )
        )
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        existing = await _load_week(db, user_id)
        if existing is None:
            raise
        return existing
    return await _load_week(db, user_id)  # type: ignore[return-value]


async def get_or_create_week(db: AsyncSession, user: User) -> StudentRoadmapWeek:
    _ensure_student(user)
    week = await _load_week(db, user.id)
    if week is None:
        week = await _seed_week(db, user.id)
    return week


async def _latest_plan_status(db: AsyncSession, user_id: int) -> tuple[bool, Optional[str]]:
    result = await db.execute(
        select(StudentGeneratedRoadmap)
        .where(StudentGeneratedRoadmap.user_id == user_id)
        .order_by(StudentGeneratedRoadmap.created_at.desc())
        .limit(1)
    )
    row = result.scalar_one_or_none()
    if row is None:
        return False, None
    available = row.status == PLAN_STATUS_READY
    return available, row.status


def serialize_roadmap(week: StudentRoadmapWeek, plan_available: bool, plan_status: Optional[str]) -> RoadmapOut:
    steps_sorted = sorted(week.steps, key=lambda s: s.step_order)
    done = [s for s in steps_sorted if s.status == STEP_STATUS_DONE]
    current = next((s for s in steps_sorted if s.status == STEP_STATUS_CURRENT), None)
    out_steps: list[RoadmapStepOut] = []
    for step in steps_sorted:
        meta = TOOL_META[step.tool_code]
        out_steps.append(
            RoadmapStepOut(
                tool_code=step.tool_code,
                order=step.step_order,
                title=meta["title"],
                minutes=meta["minutes"],
                status=step.status,
                score=step.score,
                label=step.label,
                technical_score=step.technical_score,
                communication_score=step.communication_score,
                strengths=list(step.strengths_json or []),
                weaknesses=list(step.weaknesses_json or []),
                recommendations=list(step.recommendations_json or []),
                href=meta["href"],
                completed_at=_iso(step.completed_at),
            )
        )
    return RoadmapOut(
        week_number=week.week_number,
        week_status=week.status,
        completed_count=len(done),
        total_count=len(WEEK1_STEPS),
        current_tool_code=current.tool_code if current else None,
        plan_available=plan_available,
        plan_status=plan_status,
        steps=out_steps,
    )


async def get_roadmap(db: AsyncSession, user: User) -> RoadmapOut:
    week = await get_or_create_week(db, user)
    plan_available, plan_status = await _latest_plan_status(db, user.id)
    return serialize_roadmap(week, plan_available, plan_status)


def build_analysis_from_week(week: StudentRoadmapWeek) -> AnalysisOut:
    done = [s for s in week.steps if s.status == STEP_STATUS_DONE]
    scores_by_tool: dict[str, float] = {}
    strength_counter: Counter[str] = Counter()
    weakness_counter: Counter[str] = Counter()
    recs: list[str] = []
    tech_scores: list[int] = []
    comm_scores: list[int] = []

    for step in done:
        if step.score is not None:
            scores_by_tool[step.tool_code] = float(step.score)
        for s in step.strengths_json or []:
            if isinstance(s, str) and s.strip():
                strength_counter[s.strip()] += 1
        for w in step.weaknesses_json or []:
            if isinstance(w, str) and w.strip():
                weakness_counter[w.strip()] += 1
        for r in step.recommendations_json or []:
            if isinstance(r, str) and r.strip():
                recs.append(r.strip())
            elif isinstance(r, dict) and r.get("topic"):
                recs.append(str(r["topic"]).strip())
        if step.technical_score is not None:
            tech_scores.append(int(step.technical_score))
        if step.communication_score is not None:
            comm_scores.append(int(step.communication_score))

    overall = None
    if scores_by_tool:
        overall = round(sum(scores_by_tool.values()) / len(scores_by_tool), 1)

    voice_avg = None
    if tech_scores or comm_scores:
        voice_avg = {
            "technical": round(sum(tech_scores) / len(tech_scores), 1) if tech_scores else None,
            "communication": round(sum(comm_scores) / len(comm_scores), 1) if comm_scores else None,
        }

    # unique recs preserve order
    seen: set[str] = set()
    rec_out: list[str] = []
    for r in recs:
        if r not in seen:
            seen.add(r)
            rec_out.append(r)

    return AnalysisOut(
        week_number=week.week_number,
        week_status=week.status,
        overall_score=overall,
        scores_by_tool=scores_by_tool,
        top_strengths=[k for k, _ in strength_counter.most_common(10)],
        top_weaknesses=[k for k, _ in weakness_counter.most_common(10)],
        recommendations=rec_out[:12],
        voice_avg=voice_avg,
    )


async def get_analysis(db: AsyncSession, user: User) -> AnalysisOut:
    week = await get_or_create_week(db, user)
    return build_analysis_from_week(week)


async def list_results(
    db: AsyncSession, user: User, tool_code: Optional[str] = None
) -> list[AssessmentResultOut]:
    _ensure_student(user)
    q = select(StudentAssessmentResult).where(StudentAssessmentResult.user_id == user.id)
    if tool_code:
        q = q.where(StudentAssessmentResult.tool_code == tool_code)
    q = q.order_by(StudentAssessmentResult.created_at.desc()).limit(100)
    rows = (await db.execute(q)).scalars().all()
    return [
        AssessmentResultOut(
            id=r.id,
            tool_code=r.tool_code,
            attempt_number=r.attempt_number,
            score=r.score,
            label=r.label,
            technical_score=r.technical_score,
            communication_score=r.communication_score,
            strengths=list(r.strengths_json or []),
            weaknesses=list(r.weaknesses_json or []),
            recommendations=list(r.recommendations_json or []),
            source=r.source,
            created_at=_iso(r.created_at),
        )
        for r in rows
    ]


def _recompute_week_progress(week: StudentRoadmapWeek) -> None:
    """Ensure exactly one CURRENT step (first not-done) or mark week done."""
    steps = sorted(week.steps or [], key=lambda x: x.step_order)
    if not steps:
        return
    for s in steps:
        if s.status == STEP_STATUS_CURRENT:
            s.status = STEP_STATUS_LOCKED
    first_open = next((s for s in steps if s.status != STEP_STATUS_DONE), None)
    if first_open is None:
        week.status = WEEK_STATUS_DONE
        if week.completed_at is None:
            week.completed_at = datetime.now(timezone.utc)
        return
    first_open.status = STEP_STATUS_CURRENT
    week.status = WEEK_STATUS_IN_PROGRESS
    week.completed_at = None


async def complete_step(
    db: AsyncSession, user: User, tool_code: str, body: CompleteStepRequest
) -> RoadmapOut:
    """Persist a tool result for HOD/TPO analytics.

    Product rule: always accept a completed attempt (including previously locked
    steps) so org dashboards are not blocked by sequential UI state. Week
    progress is recomputed afterward.
    """
    _ensure_student(user)
    if tool_code not in TOOL_CODES:
        raise HTTPException(status_code=404, detail=f"Unknown tool_code: {tool_code}")

    week = await get_or_create_week(db, user)
    step = next((s for s in week.steps if s.tool_code == tool_code), None)
    if step is None:
        raise HTTPException(status_code=404, detail="Step not found")

    normalized = normalize_complete_payload(body.model_dump())

    attempt_q = await db.execute(
        select(StudentAssessmentResult.attempt_number)
        .where(StudentAssessmentResult.step_id == step.id)
        .order_by(StudentAssessmentResult.attempt_number.desc())
        .limit(1)
    )
    last_attempt = attempt_q.scalar_one_or_none()
    attempt_number = int(last_attempt or 0) + 1
    source = "retake" if step.status == STEP_STATUS_DONE else "roadmap"

    result = StudentAssessmentResult(
        user_id=user.id,
        week_id=week.id,
        step_id=step.id,
        tool_code=tool_code,
        attempt_number=attempt_number,
        score=normalized["score"],
        label=normalized["label"],
        technical_score=normalized["technical_score"],
        communication_score=normalized["communication_score"],
        strengths_json=normalized["strengths"],
        weaknesses_json=normalized["weaknesses"],
        recommendations_json=normalized["recommendations"],
        raw_json=normalized["raw"],
        source=source,
    )
    db.add(result)
    await db.flush()

    now = datetime.now(timezone.utc)
    step.score = normalized["score"]
    step.label = normalized["label"]
    step.technical_score = normalized["technical_score"]
    step.communication_score = normalized["communication_score"]
    step.strengths_json = normalized["strengths"]
    step.weaknesses_json = normalized["weaknesses"]
    step.recommendations_json = normalized["recommendations"]
    step.latest_result_id = result.id
    step.completed_at = now
    step.status = STEP_STATUS_DONE

    _recompute_week_progress(week)

    await db.commit()
    week = await _load_week(db, user.id)  # type: ignore[assignment]
    plan_available, plan_status = await _latest_plan_status(db, user.id)
    return serialize_roadmap(week, plan_available, plan_status)


def serialize_plan(row: StudentGeneratedRoadmap) -> GeneratedPlanOut:
    return GeneratedPlanOut(
        id=row.id,
        status=row.status,
        prompt_version=row.prompt_version,
        model=row.model,
        summary=row.summary,
        plan=row.plan_json,
        error_message=row.error_message,
        created_at=_iso(row.created_at),
        completed_at=_iso(row.completed_at),
    )


async def get_latest_plan(db: AsyncSession, user: User) -> GeneratedPlanOut:
    _ensure_student(user)
    result = await db.execute(
        select(StudentGeneratedRoadmap)
        .where(StudentGeneratedRoadmap.user_id == user.id)
        .order_by(StudentGeneratedRoadmap.created_at.desc())
        .limit(1)
    )
    row = result.scalar_one_or_none()
    if row is None:
        raise HTTPException(status_code=404, detail="No generated plan yet.")
    return serialize_plan(row)


async def get_plan_by_id(db: AsyncSession, user: User, plan_id: int) -> GeneratedPlanOut:
    _ensure_student(user)
    result = await db.execute(
        select(StudentGeneratedRoadmap)
        .where(StudentGeneratedRoadmap.user_id == user.id)
        .where(StudentGeneratedRoadmap.id == plan_id)
    )
    row = result.scalar_one_or_none()
    if row is None:
        raise HTTPException(status_code=404, detail="Plan not found.")
    return serialize_plan(row)


def _is_stale_generating(row: StudentGeneratedRoadmap) -> bool:
    """A generating row whose worker died (deploy, crash, request abort) must not block forever."""
    if row.status != PLAN_STATUS_GENERATING:
        return False
    started = row.created_at
    if started is None:
        return True
    if started.tzinfo is None:
        started = started.replace(tzinfo=timezone.utc)
    age = (datetime.now(timezone.utc) - started).total_seconds()
    return age > PLAN_GENERATING_STALE_SECONDS


async def start_plan_generation(db: AsyncSession, user: User) -> tuple[GeneratedPlanOut, Optional[int]]:
    """
    Create (or reuse) a generating row and return it immediately.
    Second element is the plan id the caller must run in the background, or None
    when an in-flight generation is already running.
    """
    _ensure_student(user)
    week = await get_or_create_week(db, user)
    if week.status != WEEK_STATUS_DONE:
        raise HTTPException(
            status_code=409,
            detail="Complete all Week-1 baseline steps before generating the 90-day plan.",
        )

    latest_q = await db.execute(
        select(StudentGeneratedRoadmap)
        .where(StudentGeneratedRoadmap.user_id == user.id)
        .order_by(StudentGeneratedRoadmap.created_at.desc())
        .limit(1)
    )
    latest = latest_q.scalar_one_or_none()

    if latest is not None and latest.status == PLAN_STATUS_GENERATING:
        if not _is_stale_generating(latest):
            return serialize_plan(latest), None
        latest.status = PLAN_STATUS_FAILED
        latest.error_message = "Generation timed out. Please try again."
        latest.completed_at = datetime.now(timezone.utc)
        await db.flush()
    elif latest is not None and latest.status == PLAN_STATUS_READY:
        latest.status = PLAN_STATUS_SUPERSEDED
        await db.flush()

    analysis = build_analysis_from_week(week)
    snapshot = {
        **analysis.model_dump(),
        "target_companies": DEFAULT_TARGET_COMPANIES,
        "batch_year": user.batch_year,
    }

    row = StudentGeneratedRoadmap(
        user_id=user.id,
        week_id=week.id,
        status=PLAN_STATUS_GENERATING,
        prompt_version=PROMPT_VERSION,
        input_snapshot_json=snapshot,
    )
    db.add(row)
    await db.commit()
    await db.refresh(row)
    return serialize_plan(row), row.id


async def run_plan_generation(plan_id: int, llm_service: Any) -> None:
    """Background worker: call OpenAI, validate, and finalize the plan row."""
    from app.common.database.session import async_session_factory

    factory = async_session_factory()
    async with factory() as db:
        row = await db.get(StudentGeneratedRoadmap, plan_id)
        if row is None or row.status != PLAN_STATUS_GENERATING:
            return

        snapshot = row.input_snapshot_json or {}
        companies = snapshot.get("target_companies") or DEFAULT_TARGET_COMPANIES
        batch_year = snapshot.get("batch_year")

        try:
            plan_obj, summary, model_name = await llm_service.generate_placement_90day_roadmap(
                analysis=snapshot,
                target_companies=companies,
                batch_year=batch_year,
            )
            validated = validate_placement_90day_plan(plan_obj)
            row.plan_json = validated
            row.summary = (
                summary or validated.get("baseline_summary") or validated.get("confidence_goal")
            )
            row.model = model_name
            row.status = PLAN_STATUS_READY
            row.error_message = None
        except PlanValidationError as exc:
            logger.warning("Plan validation failed for plan %s: %s", plan_id, exc)
            row.status = PLAN_STATUS_FAILED
            row.error_message = f"The generated plan was incomplete. Please try again. ({exc})"[:500]
        except Exception as exc:
            logger.exception("Plan generation failed for plan %s", plan_id)
            row.status = PLAN_STATUS_FAILED
            row.error_message = str(exc)[:500] or "Failed to generate plan"

        row.completed_at = datetime.now(timezone.utc)
        await db.commit()


def build_activity_from_week(week: StudentRoadmapWeek) -> ProgressActivityOut:
    done = sorted(
        [s for s in week.steps if s.status == STEP_STATUS_DONE],
        key=lambda s: s.step_order,
    )
    current = next((s for s in week.steps if s.status == STEP_STATUS_CURRENT), None)
    return ProgressActivityOut(
        week_number=week.week_number,
        week_status=week.status,
        completed_count=len(done),
        total_count=len(WEEK1_STEPS),
        current_tool_code=current.tool_code if current else None,
        completed_steps=[
            ProgressActivityStepOut(
                tool_code=s.tool_code,
                title=(TOOL_META.get(s.tool_code) or {}).get("title") or s.tool_code,
                order=s.step_order,
                score=float(s.score) if s.score is not None else None,
                label=s.label,
                strengths=list(s.strengths_json or []),
                weaknesses=list(s.weaknesses_json or []),
                completed_at=s.completed_at.isoformat() if s.completed_at else None,
            )
            for s in done
        ],
    )


async def get_progress(db: AsyncSession, user: User) -> ProgressOut:
    week = await get_or_create_week(db, user)
    cached = None
    if isinstance(week.progress_topics_json, dict) and week.progress_topics_json:
        try:
            cached = ProgressLearningTopicsOut.model_validate(week.progress_topics_json)
        except Exception:
            logger.warning("Invalid cached progress topics for user %s", user.id)
            cached = None
    return ProgressOut(
        activity=build_activity_from_week(week),
        analysis=build_analysis_from_week(week),
        learning_topics=cached,
    )


def _normalize_topic_item(raw: Any) -> LearningTopicOut | None:
    if isinstance(raw, str) and raw.strip():
        return LearningTopicOut(topic=raw.strip())
    if not isinstance(raw, dict):
        return None
    topic = str(raw.get("topic") or "").strip()
    if not topic:
        return None
    priority = raw.get("priority", 2)
    try:
        priority = int(priority)
    except (TypeError, ValueError):
        priority = 2
    priority = min(3, max(1, priority))
    minutes = raw.get("suggested_minutes", 45)
    try:
        minutes = int(minutes)
    except (TypeError, ValueError):
        minutes = 45
    if minutes not in (30, 45, 60, 90):
        minutes = 45
    nearby = raw.get("nearby")
    nearby_s = str(nearby).strip() if nearby else None
    return LearningTopicOut(
        topic=topic[:160],
        why=str(raw.get("why") or "").strip()[:280],
        nearby=nearby_s[:160] if nearby_s else None,
        priority=priority,
        suggested_minutes=minutes,
    )


def normalize_learning_topics_payload(
    payload: dict[str, Any],
    *,
    model: str | None,
) -> ProgressLearningTopicsOut:
    from app.student_roadmap.constants import PROGRESS_TOPICS_PROMPT_VERSION

    topics_raw = payload.get("learning_topics") or {}
    pillars = ("aptitude", "skills", "interview")
    learning_topics: dict[str, list[LearningTopicOut]] = {}
    for pillar in pillars:
        items = topics_raw.get(pillar) if isinstance(topics_raw, dict) else None
        out: list[LearningTopicOut] = []
        if isinstance(items, list):
            for item in items:
                normalized = _normalize_topic_item(item)
                if normalized:
                    out.append(normalized)
        learning_topics[pillar] = out[:8]

    focus = payload.get("focus_order") or list(pillars)
    focus_order = [p for p in focus if p in pillars]
    for p in pillars:
        if p not in focus_order:
            focus_order.append(p)

    return ProgressLearningTopicsOut(
        coach_summary=str(payload.get("coach_summary") or "").strip()[:500],
        focus_order=focus_order,
        learning_topics=learning_topics,
        prompt_version=PROGRESS_TOPICS_PROMPT_VERSION,
        model=model,
        status="ready",
    )


async def generate_progress_learning_topics(
    db: AsyncSession,
    user: User,
    llm: Any,
) -> ProgressLearningTopicsOut:
    week = await get_or_create_week(db, user)
    analysis = build_analysis_from_week(week)
    activity = build_activity_from_week(week)

    if activity.completed_count < 1:
        raise HTTPException(
            status_code=409,
            detail="Complete at least one assessment or mock before generating learning topics.",
        )

    try:
        payload, model_name = await llm.generate_progress_learning_topics(
            analysis=analysis.model_dump(),
            activity=activity.model_dump(),
        )
    except Exception as exc:
        logger.exception("Progress learning topics failed for user %s", user.id)
        raise HTTPException(
            status_code=502,
            detail="Could not generate learning topics right now. Please try again.",
        ) from exc
    topics = normalize_learning_topics_payload(payload, model=model_name)
    week.progress_topics_json = topics.model_dump()
    week.progress_topics_at = datetime.now(timezone.utc)
    await db.commit()
    return topics

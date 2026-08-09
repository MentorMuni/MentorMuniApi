"""Coding assessment services: start, problem, draft, run enqueue (no Judge0 in-process)."""

from __future__ import annotations

import hashlib
import logging
from datetime import timedelta
from typing import Any, Optional

from fastapi import HTTPException
from sqlalchemy import Select, func, or_, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.coding.access import (
    assert_assessment_accessible,
    compute_seconds_remaining,
    ensure_student,
    get_owned_attempt,
    is_attempt_expired,
    mark_expired_if_needed,
    utcnow,
)
from app.coding.enums import AnalysisStatus, AssessmentStatus, AttemptStatus, ExecutionStatus, JobType, ProblemStatus
from app.coding.jobs import queue as job_queue
from app.coding.limits import get_coding_limits
from app.coding.models import (
    CodingAiAnalysis,
    CodingAssessment,
    CodingAssessmentProblem,
    CodingAttempt,
    CodingAttemptProblem,
    CodingAttemptSnapshot,
    CodingDraft,
    CodingJob,
    CodingLanguage,
    CodingProblem,
    CodingProblemVersion,
    CodingRun,
    CodingSubmission,
    CodingTestCase,
    CodingTestResult,
)
from app.coding.schemas import (
    AnalysisOut,
    AssessmentListOut,
    AssessmentSummaryOut,
    AttemptOut,
    AttemptProblemOut,
    AttemptProblemSummaryOut,
    AttemptSnapshotPayload,
    ConstraintAwarenessOut,
    DraftOut,
    DraftUpsertRequest,
    ProblemExampleOut,
    RunCaseResultOut,
    RunCreateRequest,
    RunOut,
    SnapshotProblem,
    SubmissionCreateRequest,
    SubmissionListOut,
    SubmissionOut,
    SubmissionSummaryOut,
    SubmissionTestResultOut,
)
from app.models.user import User

logger = logging.getLogger("coding")


def _parse_assessment_ref(assessment_ref: str) -> tuple[Optional[int], Optional[str]]:
    ref = (assessment_ref or "").strip()
    if not ref:
        raise HTTPException(status_code=404, detail="Assessment not found.")
    if ref.isdigit():
        return int(ref), None
    return None, ref


async def _load_assessment(db: AsyncSession, assessment_ref: str) -> CodingAssessment:
    aid, slug = _parse_assessment_ref(assessment_ref)
    q: Select[tuple[CodingAssessment]]
    if aid is not None:
        q = select(CodingAssessment).where(CodingAssessment.id == aid)
    else:
        q = select(CodingAssessment).where(CodingAssessment.slug == slug)
    row = (await db.execute(q)).scalar_one_or_none()
    if row is None:
        raise HTTPException(status_code=404, detail="Assessment not found.")
    return row


def _langs(assessment: CodingAssessment) -> list[str]:
    raw = assessment.allowed_languages_json
    if isinstance(raw, list):
        return [str(x) for x in raw]
    return ["python", "cpp", "java"]


def _placement_blurb(assessment: CodingAssessment) -> str | None:
    company = (assessment.company_name or "").strip()
    role = (assessment.role_name or "").strip()
    if company and role:
        return (
            f"Pattern practice aligned with {company} {role} screening themes. "
            "Not a guarantee of any specific interview question."
        )
    if company:
        return (
            f"Pattern practice aligned with {company} screening themes. "
            "Not a guarantee of any specific interview question."
        )
    return None


def _relevance_label(confidence: float | None) -> str | None:
    """Student-safe band — never expose raw evidence_confidence."""
    if confidence is None:
        return None
    c = float(confidence)
    if c >= 0.75:
        return "Strong pattern match"
    if c >= 0.5:
        return "Solid pattern match"
    if c >= 0.25:
        return "Exploratory match"
    return "General practice"


def _why_this_matters(
    *,
    company_name: str | None,
    role_name: str | None,
    topic: str | None,
    pattern: str | None,
) -> str | None:
    bits: list[str] = []
    if topic and pattern:
        bits.append(f"Trains the {topic} / {pattern} pattern")
    elif topic:
        bits.append(f"Trains {topic} fundamentals")
    elif pattern:
        bits.append(f"Trains the {pattern} pattern")
    if company_name and role_name:
        bits.append(f"commonly useful for {company_name} {role_name} screens")
    elif company_name:
        bits.append(f"commonly useful for {company_name} screens")
    if not bits:
        return None
    return (
        f"{bits[0].capitalize() if bits[0][0].islower() else bits[0]}"
        + (f", {bits[1]}" if len(bits) > 1 else "")
        + ". Evidence-based theme — not a specific interview question."
    )


async def _first_problem_meta(
    db: AsyncSession, assessment_id: int
) -> tuple[str | None, str | None]:
    link = (
        await db.execute(
            select(CodingAssessmentProblem)
            .where(CodingAssessmentProblem.assessment_id == assessment_id)
            .order_by(CodingAssessmentProblem.order_index.asc(), CodingAssessmentProblem.id.asc())
            .limit(1)
        )
    ).scalar_one_or_none()
    if link is None:
        return None, None
    problem = (
        await db.execute(select(CodingProblem).where(CodingProblem.id == link.problem_id))
    ).scalar_one_or_none()
    if problem is None:
        return None, None
    return problem.topic, problem.pattern


async def _assessment_summary(
    db: AsyncSession, assessment: CodingAssessment, problem_count: int
) -> AssessmentSummaryOut:
    topic, pattern = await _first_problem_meta(db, assessment.id)
    return AssessmentSummaryOut(
        id=assessment.id,
        slug=assessment.slug,
        title=assessment.title,
        difficulty=assessment.difficulty,
        duration_minutes=assessment.duration_minutes,
        status=assessment.status,
        company_key=assessment.company_key,
        company_name=assessment.company_name,
        role_name=assessment.role_name,
        placement_blurb=_placement_blurb(assessment),
        relevance_label=_relevance_label(assessment.evidence_confidence),
        topic=topic,
        pattern=pattern,
        why_this_matters=_why_this_matters(
            company_name=assessment.company_name,
            role_name=assessment.role_name,
            topic=topic,
            pattern=pattern,
        ),
        allowed_languages=_langs(assessment),
        problem_count=problem_count,
    )


async def list_assessments(
    db: AsyncSession,
    user: User,
    *,
    company_key: str | None = None,
    topic: str | None = None,
    difficulty: str | None = None,
) -> AssessmentListOut:
    ensure_student(user)
    q = (
        select(CodingAssessment)
        .where(CodingAssessment.status == AssessmentStatus.ACTIVE.value)
        .where(
            or_(
                CodingAssessment.organization_id.is_(None),
                CodingAssessment.organization_id == user.organization_id,
            )
        )
    )
    key = (company_key or "").strip().lower() or None
    if key:
        q = q.where(func.lower(CodingAssessment.company_key) == key)
    diff = (difficulty or "").strip().lower() or None
    if diff:
        q = q.where(func.lower(CodingAssessment.difficulty) == diff)
    # Evidence-backed ranking (internal confidence) — never returned raw
    q = q.order_by(
        CodingAssessment.evidence_confidence.desc().nulls_last(),
        CodingAssessment.id.asc(),
    )
    assessments = list((await db.execute(q)).scalars().all())
    topic_filter = (topic or "").strip().lower() or None
    items: list[AssessmentSummaryOut] = []
    for a in assessments:
        try:
            await assert_assessment_accessible(db, user, a, require_active=True)
        except HTTPException:
            continue
        count_row = await db.execute(
            select(CodingAssessmentProblem.id).where(CodingAssessmentProblem.assessment_id == a.id)
        )
        problem_count = len(count_row.all())
        summary = await _assessment_summary(db, a, problem_count)
        if topic_filter:
            t = (summary.topic or "").strip().lower()
            if t != topic_filter and topic_filter not in t:
                continue
        items.append(summary)
    return AssessmentListOut(items=items, company_key=key)


async def get_assessment(db: AsyncSession, user: User, assessment_ref: str) -> AssessmentSummaryOut:
    assessment = await _load_assessment(db, assessment_ref)
    await assert_assessment_accessible(db, user, assessment, require_active=True)
    count_row = await db.execute(
        select(CodingAssessmentProblem.id).where(
            CodingAssessmentProblem.assessment_id == assessment.id
        )
    )
    return await _assessment_summary(db, assessment, len(count_row.all()))


async def _build_snapshot_payload(
    db: AsyncSession, assessment: CodingAssessment
) -> AttemptSnapshotPayload:
    links = (
        await db.execute(
            select(CodingAssessmentProblem)
            .where(CodingAssessmentProblem.assessment_id == assessment.id)
            .order_by(CodingAssessmentProblem.order_index.asc(), CodingAssessmentProblem.id.asc())
        )
    ).scalars().all()
    if not links:
        raise HTTPException(status_code=400, detail="Assessment has no problems.")

    problems: list[SnapshotProblem] = []
    for link in links:
        problem = (
            await db.execute(select(CodingProblem).where(CodingProblem.id == link.problem_id))
        ).scalar_one_or_none()
        if problem is None or problem.status != ProblemStatus.PUBLISHED.value:
            raise HTTPException(status_code=400, detail="Assessment contains an unavailable problem.")
        if problem.current_version_id is None:
            raise HTTPException(status_code=400, detail="Problem has no published version.")
        version = (
            await db.execute(
                select(CodingProblemVersion).where(
                    CodingProblemVersion.id == problem.current_version_id
                )
            )
        ).scalar_one_or_none()
        if version is None:
            raise HTTPException(status_code=400, detail="Problem version missing.")
        problems.append(
            SnapshotProblem(
                problem_id=problem.id,
                problem_version_id=version.id,
                version_number=version.version_number,
                order_index=link.order_index,
                points=float(link.points),
                title=version.title,
                difficulty=version.difficulty,
                topic=version.topic,
                pattern=version.pattern,
                company_name=problem.company_name or assessment.company_name,
                role_name=problem.role_name or assessment.role_name,
            )
        )

    first_topic = problems[0].topic if problems else None
    first_pattern = problems[0].pattern if problems else None
    return AttemptSnapshotPayload(
        assessment_id=assessment.id,
        assessment_slug=assessment.slug,
        assessment_title=assessment.title,
        duration_minutes=int(assessment.duration_minutes),
        allowed_languages=_langs(assessment),
        company_key=assessment.company_key,
        company_name=assessment.company_name,
        role_name=assessment.role_name,
        placement_blurb=_placement_blurb(assessment),
        relevance_label=_relevance_label(assessment.evidence_confidence),
        why_this_matters=_why_this_matters(
            company_name=assessment.company_name,
            role_name=assessment.role_name,
            topic=first_topic,
            pattern=first_pattern,
        ),
        difficulty=assessment.difficulty,
        problems=problems,
    )


async def _attempt_out(db: AsyncSession, attempt: CodingAttempt) -> AttemptOut:
    now = utcnow()
    await mark_expired_if_needed(db, attempt)
    snap = (
        await db.execute(
            select(CodingAttemptSnapshot).where(CodingAttemptSnapshot.attempt_id == attempt.id)
        )
    ).scalar_one_or_none()
    payload = AttemptSnapshotPayload.model_validate(snap.snapshot_json) if snap else None

    ap_rows = (
        await db.execute(
            select(CodingAttemptProblem)
            .where(CodingAttemptProblem.attempt_id == attempt.id)
            .order_by(CodingAttemptProblem.order_index.asc(), CodingAttemptProblem.id.asc())
        )
    ).scalars().all()

    problems: list[AttemptProblemSummaryOut] = []
    for ap in ap_rows:
        title = ""
        difficulty = ""
        topic = None
        pattern = None
        company_name = payload.company_name if payload else None
        role_name = payload.role_name if payload else None
        if payload:
            for p in payload.problems:
                if p.problem_version_id == ap.problem_version_id:
                    title = p.title
                    difficulty = p.difficulty
                    topic = p.topic
                    pattern = p.pattern
                    company_name = p.company_name or company_name
                    role_name = p.role_name or role_name
                    break
        if not title:
            ver = (
                await db.execute(
                    select(CodingProblemVersion).where(
                        CodingProblemVersion.id == ap.problem_version_id
                    )
                )
            ).scalar_one_or_none()
            if ver:
                title = ver.title
                difficulty = ver.difficulty
                topic = ver.topic
                pattern = ver.pattern
        problems.append(
            AttemptProblemSummaryOut(
                problem_id=ap.problem_id,
                problem_version_id=ap.problem_version_id,
                order_index=ap.order_index,
                points=float(ap.points),
                title=title,
                difficulty=difficulty,
                topic=topic,
                pattern=pattern,
                company_name=company_name,
                role_name=role_name,
            )
        )

    langs = payload.allowed_languages if payload else []
    slug = payload.assessment_slug if payload else ""
    title = payload.assessment_title if payload else ""
    expired = is_attempt_expired(attempt, now) or attempt.status == AttemptStatus.EXPIRED.value
    return AttemptOut(
        id=attempt.id,
        assessment_id=attempt.assessment_id,
        assessment_slug=slug,
        assessment_title=title,
        status=attempt.status,
        starts_at=attempt.starts_at,
        ends_at=attempt.ends_at,
        submitted_at=attempt.submitted_at,
        server_now=now,
        seconds_remaining=compute_seconds_remaining(attempt.ends_at, now),
        is_expired=expired,
        company_name=payload.company_name if payload else None,
        role_name=payload.role_name if payload else None,
        placement_blurb=payload.placement_blurb if payload else None,
        relevance_label=payload.relevance_label if payload else None,
        why_this_matters=payload.why_this_matters if payload else None,
        allowed_languages=langs,
        problems=problems,
    )


async def _fetch_active_attempt(
    db: AsyncSession, *, student_id: int, assessment_id: int
) -> CodingAttempt | None:
    return (
        await db.execute(
            select(CodingAttempt)
            .where(
                CodingAttempt.student_id == student_id,
                CodingAttempt.assessment_id == assessment_id,
                CodingAttempt.status == AttemptStatus.IN_PROGRESS.value,
            )
            .order_by(CodingAttempt.id.desc())
            .limit(1)
        )
    ).scalar_one_or_none()


async def start_assessment(db: AsyncSession, user: User, assessment_ref: str) -> AttemptOut:
    """Idempotent start: reuse active in-progress attempt if still valid."""
    ensure_student(user)
    assessment = await _load_assessment(db, assessment_ref)
    await assert_assessment_accessible(db, user, assessment, require_active=True)

    # Lock existing active attempts for this student+assessment
    existing = (
        await db.execute(
            select(CodingAttempt)
            .where(
                CodingAttempt.student_id == user.id,
                CodingAttempt.assessment_id == assessment.id,
                CodingAttempt.status == AttemptStatus.IN_PROGRESS.value,
            )
            .with_for_update()
        )
    ).scalars().all()

    now = utcnow()
    for att in existing:
        if not is_attempt_expired(att, now):
            logger.info(
                "coding_start_idempotent student_id=%s assessment_id=%s attempt_id=%s",
                user.id,
                assessment.id,
                att.id,
            )
            return await _attempt_out(db, att)
        att.status = AttemptStatus.EXPIRED.value

    snapshot = await _build_snapshot_payload(db, assessment)
    # ends_at is server-only (never accepted from the client)
    ends_at = None
    if assessment.duration_minutes and assessment.duration_minutes > 0:
        ends_at = now + timedelta(minutes=int(assessment.duration_minutes))

    attempt = CodingAttempt(
        student_id=user.id,
        assessment_id=assessment.id,
        status=AttemptStatus.IN_PROGRESS.value,
        starts_at=now,
        ends_at=ends_at,
    )
    try:
        async with db.begin_nested():
            db.add(attempt)
            await db.flush()
    except IntegrityError:
        # Partial unique index blocked a concurrent second in_progress attempt.
        winner = await _fetch_active_attempt(
            db, student_id=user.id, assessment_id=assessment.id
        )
        if winner is None:
            raise HTTPException(
                status_code=409,
                detail="Could not start assessment due to a concurrent request. Retry.",
            )
        logger.info(
            "coding_start_race_resolved student_id=%s assessment_id=%s attempt_id=%s",
            user.id,
            assessment.id,
            winner.id,
        )
        return await _attempt_out(db, winner)

    db.add(
        CodingAttemptSnapshot(
            attempt_id=attempt.id,
            snapshot_json=snapshot.model_dump(mode="json"),
        )
    )
    for p in snapshot.problems:
        db.add(
            CodingAttemptProblem(
                attempt_id=attempt.id,
                problem_id=p.problem_id,
                problem_version_id=p.problem_version_id,
                order_index=p.order_index,
                points=p.points,
            )
        )
    await db.flush()
    logger.info(
        "coding_start student_id=%s assessment_id=%s attempt_id=%s",
        user.id,
        assessment.id,
        attempt.id,
    )
    return await _attempt_out(db, attempt)


async def get_attempt(db: AsyncSession, user: User, attempt_id: int) -> AttemptOut:
    attempt = await get_owned_attempt(db, user, attempt_id, allow_expired_read=True)
    return await _attempt_out(db, attempt)


def _examples_from_json(raw: Any) -> list[ProblemExampleOut]:
    out: list[ProblemExampleOut] = []
    if not isinstance(raw, list):
        return out
    for item in raw:
        if not isinstance(item, dict):
            continue
        out.append(
            ProblemExampleOut(
                input=str(item.get("input") or ""),
                output=str(item.get("output") or ""),
                explanation=(str(item["explanation"]) if item.get("explanation") is not None else None),
            )
        )
    return out


def _starter_map(raw: Any) -> dict[str, str]:
    if not isinstance(raw, dict):
        return {}
    return {str(k): str(v) for k, v in raw.items()}


def _concepts(raw: Any) -> list[str]:
    if not isinstance(raw, list):
        return []
    return [str(x) for x in raw]


async def get_attempt_problem(
    db: AsyncSession, user: User, attempt_id: int, problem_id: int
) -> AttemptProblemOut:
    attempt = await get_owned_attempt(db, user, attempt_id, allow_expired_read=True)
    ap = (
        await db.execute(
            select(CodingAttemptProblem).where(
                CodingAttemptProblem.attempt_id == attempt.id,
                CodingAttemptProblem.problem_id == problem_id,
            )
        )
    ).scalar_one_or_none()
    if ap is None:
        raise HTTPException(status_code=404, detail="Problem not part of this attempt.")

    version = (
        await db.execute(
            select(CodingProblemVersion).where(CodingProblemVersion.id == ap.problem_version_id)
        )
    ).scalar_one_or_none()
    if version is None:
        raise HTTPException(status_code=500, detail="Frozen problem version missing.")

    snap = (
        await db.execute(
            select(CodingAttemptSnapshot).where(CodingAttemptSnapshot.attempt_id == attempt.id)
        )
    ).scalar_one_or_none()
    langs: list[str] = []
    company_name = None
    role_name = None
    if snap:
        payload = AttemptSnapshotPayload.model_validate(snap.snapshot_json)
        langs = payload.allowed_languages
        company_name = payload.company_name
        role_name = payload.role_name
        for p in payload.problems:
            if p.problem_version_id == version.id:
                company_name = p.company_name or company_name
                role_name = p.role_name or role_name
                break

    now = utcnow()
    expired = is_attempt_expired(attempt, now) or attempt.status == AttemptStatus.EXPIRED.value
    # Student-safe fields ONLY — never attach test cases / reference solutions / evidence
    return AttemptProblemOut(
        attempt_id=attempt.id,
        problem_id=ap.problem_id,
        problem_version_id=version.id,
        version_number=version.version_number,
        title=version.title,
        description=version.description,
        difficulty=version.difficulty,
        topic=version.topic,
        subtopic=version.subtopic,
        pattern=version.pattern,
        company_name=company_name,
        role_name=role_name,
        constraints_text=version.constraints_text,
        input_format=version.input_format,
        output_format=version.output_format,
        examples=_examples_from_json(version.examples_json),
        concepts=_concepts(version.concepts_json),
        starter_code_by_language=_starter_map(version.starter_code_by_language),
        allowed_languages=langs,
        time_limit_ms=version.time_limit_ms,
        memory_limit_kb=version.memory_limit_kb,
        points=float(ap.points),
        order_index=ap.order_index,
        attempt_status=attempt.status,
        ends_at=attempt.ends_at,
        server_now=now,
        seconds_remaining=compute_seconds_remaining(attempt.ends_at, now),
        is_expired=expired,
    )


async def _resolve_attempt_problem_version(
    db: AsyncSession, attempt: CodingAttempt, problem_id: int
) -> CodingAttemptProblem:
    ap = (
        await db.execute(
            select(CodingAttemptProblem).where(
                CodingAttemptProblem.attempt_id == attempt.id,
                CodingAttemptProblem.problem_id == problem_id,
            )
        )
    ).scalar_one_or_none()
    if ap is None:
        raise HTTPException(status_code=404, detail="Problem not part of this attempt.")
    return ap


async def upsert_draft(
    db: AsyncSession, user: User, attempt_id: int, problem_id: int, body: DraftUpsertRequest
) -> DraftOut:
    attempt = await get_owned_attempt(db, user, attempt_id, allow_expired_read=True)
    if attempt.status != AttemptStatus.IN_PROGRESS.value or is_attempt_expired(attempt):
        if attempt.status == AttemptStatus.IN_PROGRESS.value:
            await mark_expired_if_needed(db, attempt)
        raise HTTPException(status_code=409, detail="Cannot save draft for this attempt state.")

    ap = await _resolve_attempt_problem_version(db, attempt, problem_id)
    lang = body.language_code.strip().lower()
    snap = (
        await db.execute(
            select(CodingAttemptSnapshot).where(CodingAttemptSnapshot.attempt_id == attempt.id)
        )
    ).scalar_one_or_none()
    if snap:
        payload = AttemptSnapshotPayload.model_validate(snap.snapshot_json)
        allowed = {x.lower() for x in payload.allowed_languages}
        if lang not in allowed:
            raise HTTPException(status_code=400, detail="Language not allowed for this attempt.")

    limits = get_coding_limits()
    source = body.source_code or ""
    if len(source.encode("utf-8")) > limits.max_source_bytes:
        raise HTTPException(status_code=413, detail="Source code exceeds maximum allowed size.")

    now = utcnow()
    stmt = (
        pg_insert(CodingDraft)
        .values(
            attempt_id=attempt.id,
            problem_version_id=ap.problem_version_id,
            language_code=lang,
            source_code=source,
            updated_at=now,
            created_at=now,
        )
        .on_conflict_do_update(
            constraint="uq_coding_drafts_attempt_version_lang",
            set_={
                "source_code": source,
                "updated_at": now,
            },
        )
        .returning(CodingDraft.id, CodingDraft.created_at, CodingDraft.updated_at)
    )
    row = (await db.execute(stmt)).one()
    return DraftOut(
        id=int(row.id),
        attempt_id=attempt.id,
        problem_id=problem_id,
        problem_version_id=ap.problem_version_id,
        language_code=lang,
        source_code=source,
        updated_at=row.updated_at,
        created_at=row.created_at,
    )


async def get_draft(
    db: AsyncSession,
    user: User,
    attempt_id: int,
    problem_id: int,
    language_code: str,
) -> DraftOut:
    attempt = await get_owned_attempt(db, user, attempt_id, allow_expired_read=True)
    ap = await _resolve_attempt_problem_version(db, attempt, problem_id)
    lang = language_code.strip().lower()
    draft = (
        await db.execute(
            select(CodingDraft).where(
                CodingDraft.attempt_id == attempt.id,
                CodingDraft.problem_version_id == ap.problem_version_id,
                CodingDraft.language_code == lang,
            )
        )
    ).scalar_one_or_none()
    if draft is None:
        raise HTTPException(status_code=404, detail="Draft not found.")
    return DraftOut(
        id=draft.id,
        attempt_id=attempt.id,
        problem_id=problem_id,
        problem_version_id=ap.problem_version_id,
        language_code=draft.language_code,
        source_code=draft.source_code,
        updated_at=draft.updated_at,
        created_at=draft.created_at,
    )


def _source_hash(source: str) -> str:
    return hashlib.sha256(source.encode("utf-8")).hexdigest()


async def _assert_run_rate_limit(db: AsyncSession, student_id: int) -> None:
    limits = get_coding_limits()
    since = utcnow() - timedelta(seconds=limits.run_rate_window_seconds)
    count = (
        await db.execute(
            select(func.count())
            .select_from(CodingRun)
            .where(CodingRun.student_id == student_id, CodingRun.created_at >= since)
        )
    ).scalar_one()
    if int(count or 0) >= limits.run_rate_per_student:
        raise HTTPException(
            status_code=429,
            detail="Too many Run Code requests. Please wait and try again.",
        )


def _run_out(run: CodingRun, *, problem_id: int, job_id: int | None = None) -> RunOut:
    cases: list[RunCaseResultOut] = []
    summary = run.result_summary_json if isinstance(run.result_summary_json, dict) else {}
    raw_cases = summary.get("cases") if isinstance(summary.get("cases"), list) else []
    for item in raw_cases:
        if not isinstance(item, dict):
            continue
        cases.append(
            RunCaseResultOut(
                index=int(item.get("index") or 0),
                status=str(item.get("status") or ""),
                verdict=(str(item["verdict"]) if item.get("verdict") is not None else None),
                execution_time_ms=item.get("execution_time_ms"),
                memory_used_kb=item.get("memory_used_kb"),
                error_type=(str(item["error_type"]) if item.get("error_type") else None),
                compile_output=(str(item["compile_output"]) if item.get("compile_output") else None),
                stderr=(str(item["stderr"]) if item.get("stderr") else None),
            )
        )
    return RunOut(
        id=run.id,
        job_id=job_id,
        attempt_id=run.attempt_id,
        problem_id=problem_id,
        problem_version_id=run.problem_version_id,
        language_code=run.language_code,
        execution_status=run.execution_status,
        verdict=run.verdict,
        passed_count=int(run.passed_count or 0),
        total_count=int(run.total_count or 0),
        execution_time_ms=run.execution_time_ms,
        memory_used_kb=run.memory_used_kb,
        cases=cases,
        created_at=run.created_at,
    )


async def enqueue_run(db: AsyncSession, user: User, body: RunCreateRequest) -> RunOut:
    """Create coding_run + coding_jobs row. Worker executes via Judge0 (never in this request)."""
    ensure_student(user)
    attempt = await get_owned_attempt(db, user, body.attempt_id, allow_expired_read=True)
    if attempt.status != AttemptStatus.IN_PROGRESS.value or is_attempt_expired(attempt):
        if attempt.status == AttemptStatus.IN_PROGRESS.value:
            await mark_expired_if_needed(db, attempt)
        raise HTTPException(status_code=409, detail="Cannot run code for this attempt state.")

    await _assert_run_rate_limit(db, user.id)
    ap = await _resolve_attempt_problem_version(db, attempt, body.problem_id)

    lang = body.language_code.strip().lower()
    snap = (
        await db.execute(
            select(CodingAttemptSnapshot).where(CodingAttemptSnapshot.attempt_id == attempt.id)
        )
    ).scalar_one_or_none()
    if snap:
        payload = AttemptSnapshotPayload.model_validate(snap.snapshot_json)
        allowed = {x.lower() for x in payload.allowed_languages}
        if lang not in allowed:
            raise HTTPException(status_code=400, detail="Language not allowed for this attempt.")

    language_row = (
        await db.execute(
            select(CodingLanguage).where(
                CodingLanguage.code == lang,
                CodingLanguage.is_active.is_(True),
            )
        )
    ).scalar_one_or_none()
    if language_row is None:
        raise HTTPException(status_code=400, detail="Unsupported language.")

    limits = get_coding_limits()
    source = body.source_code or ""
    if not source.strip():
        raise HTTPException(status_code=400, detail="Source code is empty.")
    if len(source.encode("utf-8")) > limits.max_source_bytes:
        raise HTTPException(status_code=413, detail="Source code exceeds maximum allowed size.")

    run = CodingRun(
        student_id=user.id,
        attempt_id=attempt.id,
        problem_version_id=ap.problem_version_id,
        language_code=lang,
        source_code=source,
        source_hash=_source_hash(source),
        execution_status=ExecutionStatus.QUEUED.value,
        passed_count=0,
        total_count=0,
    )
    db.add(run)
    await db.flush()

    job = await job_queue.enqueue_job(
        db,
        job_type=JobType.RUN,
        student_id=user.id,
        attempt_id=attempt.id,
        run_id=run.id,
        payload={"problem_id": body.problem_id, "language_code": lang},
    )
    logger.info(
        "coding_run_enqueued run_id=%s job_id=%s student_id=%s attempt_id=%s",
        run.id,
        job.id,
        user.id,
        attempt.id,
    )
    return _run_out(run, problem_id=body.problem_id, job_id=job.id)


async def get_run(db: AsyncSession, user: User, run_id: int) -> RunOut:
    ensure_student(user)
    run = (await db.execute(select(CodingRun).where(CodingRun.id == run_id))).scalar_one_or_none()
    if run is None or run.student_id != user.id:
        raise HTTPException(status_code=404, detail="Run not found.")

    ap = (
        await db.execute(
            select(CodingAttemptProblem).where(
                CodingAttemptProblem.attempt_id == run.attempt_id,
                CodingAttemptProblem.problem_version_id == run.problem_version_id,
            )
        )
    ).scalar_one_or_none()
    problem_id = ap.problem_id if ap else 0

    job = (
        await db.execute(
            select(CodingJob)
            .where(CodingJob.run_id == run.id)
            .order_by(CodingJob.id.desc())
            .limit(1)
        )
    ).scalar_one_or_none()
    return _run_out(run, problem_id=problem_id, job_id=job.id if job else None)


async def _assert_submit_rate_limit(db: AsyncSession, student_id: int) -> None:
    limits = get_coding_limits()
    since = utcnow() - timedelta(seconds=limits.submit_rate_window_seconds)
    count = (
        await db.execute(
            select(func.count())
            .select_from(CodingSubmission)
            .where(CodingSubmission.student_id == student_id, CodingSubmission.created_at >= since)
        )
    ).scalar_one()
    if int(count or 0) >= limits.submit_rate_per_student:
        raise HTTPException(
            status_code=429,
            detail="Too many submissions. Please wait and try again.",
        )


async def _submission_out(
    db: AsyncSession,
    sub: CodingSubmission,
    *,
    job_id: int | None = None,
) -> SubmissionOut:
    cases = (
        await db.execute(
            select(CodingTestCase)
            .where(CodingTestCase.problem_version_id == sub.problem_version_id)
            .order_by(CodingTestCase.order_index.asc(), CodingTestCase.id.asc())
        )
    ).scalars().all()
    results = (
        await db.execute(
            select(CodingTestResult).where(CodingTestResult.submission_id == sub.id)
        )
    ).scalars().all()
    by_case = {r.test_case_id: r for r in results}

    out_results: list[SubmissionTestResultOut] = []
    passed = public_passed = hidden_passed = 0
    public_total = hidden_total = 0
    for i, tc in enumerate(cases):
        tr = by_case.get(tc.id)
        status = tr.status if tr else ("pending" if sub.execution_status in ("queued", "running") else "skipped")
        if tr and tr.status == "passed":
            passed += 1
            if tc.is_hidden:
                hidden_passed += 1
            else:
                public_passed += 1
        if tc.is_hidden:
            hidden_total += 1
        else:
            public_total += 1
        out_results.append(
            SubmissionTestResultOut(
                index=i,
                hidden=bool(tc.is_hidden),
                status=status,
                weight=float(tc.weight or 1.0),
                execution_time_ms=tr.execution_time_ms if tr else None,
                memory_used_kb=tr.memory_used_kb if tr else None,
                error_type=tr.error_type if tr else None,
                actual_output=(tr.actual_output if tr and not tc.is_hidden else None),
            )
        )

    version = (
        await db.execute(
            select(CodingProblemVersion).where(CodingProblemVersion.id == sub.problem_version_id)
        )
    ).scalar_one_or_none()
    assessment = (
        await db.execute(select(CodingAssessment).where(CodingAssessment.id == sub.assessment_id))
    ).scalar_one_or_none()

    return SubmissionOut(
        id=sub.id,
        job_id=job_id,
        attempt_id=sub.attempt_id,
        assessment_id=sub.assessment_id,
        assessment_title=assessment.title if assessment else None,
        problem_id=sub.problem_id,
        problem_title=version.title if version else None,
        problem_version_id=sub.problem_version_id,
        company_name=assessment.company_name if assessment else None,
        role_name=assessment.role_name if assessment else None,
        language_code=sub.language_code,
        execution_status=sub.execution_status,
        verdict=sub.verdict,
        analysis_status=sub.analysis_status,
        official_score=float(sub.score) if sub.score is not None else None,
        passed_count=passed,
        total_count=len(cases),
        public_passed_count=public_passed,
        public_total_count=public_total,
        hidden_passed_count=hidden_passed,
        hidden_total_count=hidden_total,
        execution_time_ms=sub.execution_time_ms,
        memory_used_kb=sub.memory_used_kb,
        test_results=out_results,
        submitted_at=sub.submitted_at,
        created_at=sub.created_at,
    )


async def enqueue_submission(
    db: AsyncSession, user: User, body: SubmissionCreateRequest
) -> SubmissionOut:
    """Create immutable submission + submit_evaluate job. Official score set by worker."""
    ensure_student(user)
    attempt = await get_owned_attempt(db, user, body.attempt_id, allow_expired_read=True)
    if attempt.status != AttemptStatus.IN_PROGRESS.value or is_attempt_expired(attempt):
        if attempt.status == AttemptStatus.IN_PROGRESS.value:
            await mark_expired_if_needed(db, attempt)
        raise HTTPException(status_code=409, detail="Cannot submit for this attempt state.")

    await _assert_submit_rate_limit(db, user.id)
    ap = await _resolve_attempt_problem_version(db, attempt, body.problem_id)

    lang = body.language_code.strip().lower()
    snap = (
        await db.execute(
            select(CodingAttemptSnapshot).where(CodingAttemptSnapshot.attempt_id == attempt.id)
        )
    ).scalar_one_or_none()
    if snap:
        payload = AttemptSnapshotPayload.model_validate(snap.snapshot_json)
        allowed = {x.lower() for x in payload.allowed_languages}
        if lang not in allowed:
            raise HTTPException(status_code=400, detail="Language not allowed for this attempt.")

    language_row = (
        await db.execute(
            select(CodingLanguage).where(
                CodingLanguage.code == lang,
                CodingLanguage.is_active.is_(True),
            )
        )
    ).scalar_one_or_none()
    if language_row is None:
        raise HTTPException(status_code=400, detail="Unsupported language.")

    limits = get_coding_limits()
    source = body.source_code or ""
    if not source.strip():
        raise HTTPException(status_code=400, detail="Source code is empty.")
    if len(source.encode("utf-8")) > limits.max_source_bytes:
        raise HTTPException(status_code=413, detail="Source code exceeds maximum allowed size.")

    now = utcnow()
    sub = CodingSubmission(
        student_id=user.id,
        attempt_id=attempt.id,
        assessment_id=attempt.assessment_id,
        problem_id=body.problem_id,
        problem_version_id=ap.problem_version_id,
        language_code=lang,
        source_code=source,
        source_hash=_source_hash(source),
        execution_status=ExecutionStatus.QUEUED.value,
        analysis_status=AnalysisStatus.PENDING.value,
        submitted_at=now,
    )
    db.add(sub)

    # Freeze attempt on submit (MVP: one problem assessments; multi-problem can refine later)
    attempt.status = AttemptStatus.SUBMITTED.value
    attempt.submitted_at = now
    await db.flush()

    job = await job_queue.enqueue_job(
        db,
        job_type=JobType.SUBMIT_EVALUATE,
        student_id=user.id,
        attempt_id=attempt.id,
        submission_id=sub.id,
        payload={"problem_id": body.problem_id, "language_code": lang},
    )
    logger.info(
        "coding_submission_enqueued submission_id=%s job_id=%s student_id=%s attempt_id=%s",
        sub.id,
        job.id,
        user.id,
        attempt.id,
    )
    return await _submission_out(db, sub, job_id=job.id)


async def get_submission(db: AsyncSession, user: User, submission_id: int) -> SubmissionOut:
    ensure_student(user)
    sub = (
        await db.execute(select(CodingSubmission).where(CodingSubmission.id == submission_id))
    ).scalar_one_or_none()
    if sub is None or sub.student_id != user.id:
        raise HTTPException(status_code=404, detail="Submission not found.")

    job = (
        await db.execute(
            select(CodingJob)
            .where(
                CodingJob.submission_id == sub.id,
                CodingJob.job_type == JobType.SUBMIT_EVALUATE.value,
            )
            .order_by(CodingJob.id.desc())
            .limit(1)
        )
    ).scalar_one_or_none()
    return await _submission_out(db, sub, job_id=job.id if job else None)


async def get_submission_analysis(
    db: AsyncSession, user: User, submission_id: int
) -> AnalysisOut:
    ensure_student(user)
    sub = (
        await db.execute(select(CodingSubmission).where(CodingSubmission.id == submission_id))
    ).scalar_one_or_none()
    if sub is None or sub.student_id != user.id:
        raise HTTPException(status_code=404, detail="Submission not found.")

    analysis = (
        await db.execute(
            select(CodingAiAnalysis).where(CodingAiAnalysis.submission_id == sub.id)
        )
    ).scalar_one_or_none()

    if analysis is None:
        return AnalysisOut(
            submission_id=sub.id,
            analysis_status=sub.analysis_status,
            official_score=float(sub.score) if sub.score is not None else None,
            official_verdict=sub.verdict,
        )

    payload = analysis.analysis_json if isinstance(analysis.analysis_json, dict) else {}
    return AnalysisOut(
        submission_id=sub.id,
        analysis_status=sub.analysis_status,
        prompt_version=analysis.prompt_version,
        overall_coaching_score=analysis.overall_coaching_score,
        correctness_coaching_score=analysis.correctness_coaching_score,
        approach_score=analysis.approach_score,
        complexity_score=analysis.complexity_score,
        code_quality_score=analysis.code_quality_score,
        edge_case_score=analysis.edge_case_score,
        constraint_awareness=ConstraintAwarenessOut(
            understood_constraints=analysis.understood_constraints,
            complexity_appropriate_for_constraints=analysis.complexity_appropriate_for_constraints,
            missed_scalable_approach=analysis.missed_scalable_approach,
            notes=analysis.constraint_notes,
        ),
        detected_approach=analysis.detected_approach,
        time_complexity=analysis.time_complexity,
        space_complexity=analysis.space_complexity,
        beginner_explanation=str(payload.get("beginner_explanation") or "") or None,
        mistakes=list(payload.get("mistakes") or []) if isinstance(payload.get("mistakes"), list) else [],
        better_approach=payload.get("better_approach")
        if isinstance(payload.get("better_approach"), dict)
        else None,
        strengths=list(payload.get("strengths") or []) if isinstance(payload.get("strengths"), list) else [],
        learning_gaps=list(payload.get("learning_gaps") or [])
        if isinstance(payload.get("learning_gaps"), list)
        else [],
        next_learning_focus=list(payload.get("next_learning_focus") or [])
        if isinstance(payload.get("next_learning_focus"), list)
        else [],
        official_score=float(sub.score) if sub.score is not None else None,
        official_verdict=sub.verdict,
    )


async def list_submissions(
    db: AsyncSession,
    user: User,
    *,
    limit: int = 20,
    company_key: str | None = None,
) -> SubmissionListOut:
    """Past submissions for result revisit (newest first)."""
    ensure_student(user)
    lim = max(1, min(int(limit or 20), 50))
    q = (
        select(CodingSubmission)
        .where(CodingSubmission.student_id == user.id)
        .order_by(CodingSubmission.submitted_at.desc(), CodingSubmission.id.desc())
        .limit(lim)
    )
    key = (company_key or "").strip().lower() or None
    if key:
        q = (
            select(CodingSubmission)
            .join(CodingAssessment, CodingAssessment.id == CodingSubmission.assessment_id)
            .where(
                CodingSubmission.student_id == user.id,
                func.lower(CodingAssessment.company_key) == key,
            )
            .order_by(CodingSubmission.submitted_at.desc(), CodingSubmission.id.desc())
            .limit(lim)
        )
    rows = list((await db.execute(q)).scalars().all())
    items: list[SubmissionSummaryOut] = []
    for sub in rows:
        assessment = (
            await db.execute(select(CodingAssessment).where(CodingAssessment.id == sub.assessment_id))
        ).scalar_one_or_none()
        version = (
            await db.execute(
                select(CodingProblemVersion).where(CodingProblemVersion.id == sub.problem_version_id)
            )
        ).scalar_one_or_none()
        items.append(
            SubmissionSummaryOut(
                id=sub.id,
                attempt_id=sub.attempt_id,
                assessment_id=sub.assessment_id,
                assessment_slug=assessment.slug if assessment else None,
                assessment_title=assessment.title if assessment else None,
                problem_id=sub.problem_id,
                problem_title=version.title if version else None,
                company_name=assessment.company_name if assessment else None,
                role_name=assessment.role_name if assessment else None,
                language_code=sub.language_code,
                execution_status=sub.execution_status,
                verdict=sub.verdict,
                analysis_status=sub.analysis_status,
                official_score=float(sub.score) if sub.score is not None else None,
                submitted_at=sub.submitted_at,
            )
        )
    return SubmissionListOut(items=items)

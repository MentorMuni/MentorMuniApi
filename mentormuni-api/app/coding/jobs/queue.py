"""Postgres-backed job queue for CodingJobWorker (not FastAPI BackgroundTasks)."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from sqlalchemy import func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.coding.enums import JobStatus, JobType
from app.coding.limits import get_coding_limits
from app.coding.models import CodingJob
from app.core.config import settings

logger = logging.getLogger("coding.jobs")


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


async def enqueue_job(
    db: AsyncSession,
    *,
    job_type: JobType | str,
    student_id: int | None = None,
    attempt_id: int | None = None,
    run_id: int | None = None,
    submission_id: int | None = None,
    payload: dict[str, Any] | None = None,
) -> CodingJob:
    job = CodingJob(
        job_type=job_type.value if isinstance(job_type, JobType) else str(job_type),
        status=JobStatus.PENDING.value,
        student_id=student_id,
        attempt_id=attempt_id,
        run_id=run_id,
        submission_id=submission_id,
        payload_json=payload or {},
        attempt_count=0,
    )
    db.add(job)
    await db.flush()
    logger.info(
        "coding_job_enqueued id=%s type=%s run_id=%s submission_id=%s",
        job.id,
        job.job_type,
        run_id,
        submission_id,
    )
    return job


async def count_active_jobs(db: AsyncSession) -> int:
    result = await db.execute(
        select(func.count())
        .select_from(CodingJob)
        .where(CodingJob.status.in_([JobStatus.CLAIMED.value, JobStatus.RUNNING.value]))
    )
    return int(result.scalar_one() or 0)


async def recover_stale_jobs(db: AsyncSession) -> int:
    """Re-queue claimed/running jobs that have been stuck too long."""
    stale_seconds = int(getattr(settings, "coding_job_stale_seconds", 300) or 300)
    cutoff = utcnow() - timedelta(seconds=stale_seconds)
    result = await db.execute(
        update(CodingJob)
        .where(
            CodingJob.status.in_([JobStatus.CLAIMED.value, JobStatus.RUNNING.value]),
            CodingJob.claimed_at.is_not(None),
            CodingJob.claimed_at < cutoff,
        )
        .values(
            status=JobStatus.PENDING.value,
            claimed_at=None,
            provider_status="stale_requeued",
            last_error="Stale job requeued by worker recovery",
            next_retry_at=None,
            updated_at=utcnow(),
        )
        .returning(CodingJob.id)
    )
    ids = list(result.scalars().all())
    if ids:
        logger.warning("coding_jobs_stale_requeued count=%s ids=%s", len(ids), ids[:20])
    return len(ids)


async def claim_next_job(db: AsyncSession) -> CodingJob | None:
    """Claim one due pending job under concurrency limit (SKIP LOCKED)."""
    limits = get_coding_limits()
    active = await count_active_jobs(db)
    if active >= limits.max_concurrent_jobs:
        return None

    now = utcnow()
    result = await db.execute(
        select(CodingJob)
        .where(
            CodingJob.status == JobStatus.PENDING.value,
            or_(CodingJob.next_retry_at.is_(None), CodingJob.next_retry_at <= now),
        )
        .order_by(CodingJob.id.asc())
        .limit(1)
        .with_for_update(skip_locked=True)
    )
    job = result.scalar_one_or_none()
    if job is None:
        return None

    job.status = JobStatus.CLAIMED.value
    job.claimed_at = now
    job.attempt_count = int(job.attempt_count or 0) + 1
    job.updated_at = now
    await db.flush()
    logger.info("coding_job_claimed id=%s type=%s attempt_count=%s", job.id, job.job_type, job.attempt_count)
    return job


async def mark_running(db: AsyncSession, job: CodingJob) -> None:
    job.status = JobStatus.RUNNING.value
    job.updated_at = utcnow()
    await db.flush()


async def update_provider_meta(
    db: AsyncSession,
    job: CodingJob,
    *,
    provider: str | None = None,
    token: str | None = None,
    provider_status: str | None = None,
) -> None:
    if provider is not None:
        job.provider = provider
    if token is not None:
        job.provider_submission_token = token[:128]
    if provider_status is not None:
        job.provider_status = provider_status[:64]
    job.updated_at = utcnow()
    await db.flush()


async def mark_succeeded(db: AsyncSession, job: CodingJob) -> None:
    job.status = JobStatus.SUCCEEDED.value
    job.completed_at = utcnow()
    job.next_retry_at = None
    job.last_error = None
    job.updated_at = utcnow()
    await db.flush()
    logger.info("coding_job_succeeded id=%s", job.id)


async def mark_failed(
    db: AsyncSession,
    job: CodingJob,
    *,
    error: str,
    retryable: bool = True,
) -> None:
    limits = get_coding_limits()
    job.last_error = (error or "unknown")[:2000]
    job.updated_at = utcnow()
    if retryable and int(job.attempt_count or 0) < limits.job_max_attempts:
        backoff = min(300, 2 ** min(int(job.attempt_count or 1), 8))
        job.status = JobStatus.PENDING.value
        job.next_retry_at = utcnow() + timedelta(seconds=backoff)
        job.claimed_at = None
        job.provider_status = "retry_scheduled"
        logger.warning(
            "coding_job_retry id=%s attempt_count=%s backoff_s=%s err=%s",
            job.id,
            job.attempt_count,
            backoff,
            error[:200],
        )
    else:
        job.status = JobStatus.DEAD.value
        job.completed_at = utcnow()
        logger.error("coding_job_dead id=%s err=%s", job.id, error[:200])
    await db.flush()

"""Authorization and lifecycle helpers for coding assessments."""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.coding.enums import AssessmentStatus, AttemptStatus
from app.coding.models import CodingAssessment, CodingAttempt
from app.models.feature_catalog import FeatureCatalog
from app.models.organization_feature import OrganizationFeature
from app.models.user import User

CODING_FEATURE_CODE = "coding"


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def ensure_student(user: User) -> None:
    code = user.role.role_code if user.role else None
    if code != "STUDENT":
        raise HTTPException(status_code=403, detail="Student role required.")


async def org_has_coding_feature(db: AsyncSession, organization_id: int) -> bool:
    result = await db.execute(
        select(OrganizationFeature.id)
        .join(FeatureCatalog, FeatureCatalog.id == OrganizationFeature.feature_id)
        .where(
            OrganizationFeature.organization_id == organization_id,
            OrganizationFeature.enabled.is_(True),
            FeatureCatalog.feature_code == CODING_FEATURE_CODE,
        )
        .limit(1)
    )
    return result.scalar_one_or_none() is not None


async def assert_assessment_accessible(
    db: AsyncSession,
    user: User,
    assessment: CodingAssessment,
    *,
    require_active: bool = True,
) -> None:
    """Tenant rules: platform (org_id NULL) for all students; org-scoped for matching org."""
    ensure_student(user)
    if require_active and assessment.status != AssessmentStatus.ACTIVE.value:
        raise HTTPException(status_code=404, detail="Assessment not available.")

    if assessment.organization_id is None:
        return

    if user.organization_id != assessment.organization_id:
        raise HTTPException(status_code=404, detail="Assessment not available.")

    has_feature = await org_has_coding_feature(db, user.organization_id)
    if not has_feature:
        raise HTTPException(
            status_code=403,
            detail="Coding assessments are not enabled for your organization.",
        )


def compute_seconds_remaining(ends_at: datetime | None, now: datetime | None = None) -> int | None:
    if ends_at is None:
        return None
    now = now or utcnow()
    if ends_at.tzinfo is None:
        ends_at = ends_at.replace(tzinfo=timezone.utc)
    delta = int((ends_at - now).total_seconds())
    return max(0, delta)


def is_attempt_expired(attempt: CodingAttempt, now: datetime | None = None) -> bool:
    if attempt.status == AttemptStatus.EXPIRED.value:
        return True
    if attempt.ends_at is None:
        return False
    now = now or utcnow()
    ends = attempt.ends_at
    if ends.tzinfo is None:
        ends = ends.replace(tzinfo=timezone.utc)
    return now >= ends


async def mark_expired_if_needed(db: AsyncSession, attempt: CodingAttempt) -> CodingAttempt:
    if attempt.status == AttemptStatus.IN_PROGRESS.value and is_attempt_expired(attempt):
        attempt.status = AttemptStatus.EXPIRED.value
        await db.flush()
    return attempt


async def get_owned_attempt(
    db: AsyncSession,
    user: User,
    attempt_id: int,
    *,
    allow_expired_read: bool = True,
) -> CodingAttempt:
    ensure_student(user)
    result = await db.execute(select(CodingAttempt).where(CodingAttempt.id == attempt_id))
    attempt = result.scalar_one_or_none()
    if attempt is None or attempt.student_id != user.id:
        raise HTTPException(status_code=404, detail="Attempt not found.")
    await mark_expired_if_needed(db, attempt)
    if not allow_expired_read and attempt.status == AttemptStatus.EXPIRED.value:
        raise HTTPException(status_code=409, detail="This attempt has expired.")
    return attempt

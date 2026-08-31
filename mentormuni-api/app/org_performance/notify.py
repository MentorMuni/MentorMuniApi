"""Notify student cohorts from performance analytics."""

from __future__ import annotations

from typing import Optional

from fastapi import BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.tenant.context import TenantContext
from app.models.enums import NotificationAudience, NotificationKind
from app.notifications import service as notif_service
from app.org_performance import service as perf_service
from app.org_performance.cohort import resolve_cohort_student_ids
from app.org_performance.schemas import NotifyCohortOut, NotifyCohortRequest
from app.org_performance.service import PerformanceError


async def notify_performance_cohort(
    db: AsyncSession,
    ctx: TenantContext,
    body: NotifyCohortRequest,
    *,
    background_tasks: BackgroundTasks | None = None,
) -> NotifyCohortOut:
    if not ctx.has_permission("SEND_NOTIFICATION"):
        raise PerformanceError("SEND_NOTIFICATION permission required.", status_code=403)

    dept_id = body.department_id
    if not ctx.sees_all_students:
        if ctx.department_id is None:
            raise PerformanceError("HOD account is not linked to a department.")
        dept_id = ctx.department_id
    elif dept_id is not None and not ctx.sees_all_students:
        raise PerformanceError("Not allowed.", status_code=403)

    summary = await perf_service.get_performance_summary(db, ctx, department_id=dept_id)
    cards = summary.scorecards
    at_risk_ids = {s.id for s in summary.at_risk}

    if body.cohort == "custom" and not body.student_ids:
        raise PerformanceError("student_ids required for custom cohort.")

    try:
        student_ids = resolve_cohort_student_ids(
            body.cohort,
            cards,
            at_risk_ids,
            custom_ids=body.student_ids,
        )
    except ValueError as exc:
        raise PerformanceError(str(exc)) from exc

    if body.max_recipients and len(student_ids) > body.max_recipients:
        student_ids = student_ids[: body.max_recipients]

    if not student_ids:
        return NotifyCohortOut(
            ok=True,
            recipients=0,
            message="No students matched this cohort.",
        )

    notif = await notif_service.create_notification(
        db,
        ctx=ctx,
        title=body.title,
        body=body.message,
        audience=NotificationAudience.USERS.value,
        user_ids=student_ids,
        kind=NotificationKind.ANNOUNCEMENT.value,
        metadata_json={"source": "performance_cohort", "cohort": body.cohort},
    )

    if background_tasks is not None:
        background_tasks.add_task(notif_service.deliver_notification_emails, notif.id)

    return NotifyCohortOut(
        ok=True,
        notification_id=notif.id,
        recipients=len(student_ids),
        delivery_status=getattr(notif, "delivery_status", None) or "queued",
        message=f"Notification queued for {len(student_ids)} student(s).",
    )

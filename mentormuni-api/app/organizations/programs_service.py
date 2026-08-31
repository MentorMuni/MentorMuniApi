"""Campus program / assessment assignments — stored as notifications (kind=program)."""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from typing import Any, Optional

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.common.tenant.context import TenantContext
from app.models.enums import NotificationAudience, NotificationKind
from app.models.notification import Notification
from app.models.notification_recipient import NotificationRecipient
from app.notifications import service as notif_service
from app.organizations.programs_schemas import ProgramOut


class ProgramError(Exception):
    def __init__(self, message: str, *, status_code: int = 400) -> None:
        super().__init__(message)
        self.message = message
        self.status_code = status_code


def _fe_audience(stored: str) -> str:
    if stored == NotificationAudience.USERS.value:
        return "student"
    if stored == NotificationAudience.DEPARTMENT.value:
        return "department"
    return "all"


def _event_date(n: Notification) -> Optional[date]:
    if n.event_date is None:
        return None
    if hasattr(n.event_date, "date"):
        return n.event_date.date()
    return n.event_date  # type: ignore[return-value]


def notification_to_program(n: Notification, *, recipients_estimated: int = 0) -> ProgramOut:
    meta = n.metadata_json if isinstance(n.metadata_json, dict) else {}
    raw_ids = meta.get("student_ids") or []
    student_ids: list[int] = []
    if isinstance(raw_ids, list):
        for x in raw_ids:
            try:
                student_ids.append(int(x))
            except (TypeError, ValueError):
                continue
    raw_dept_ids = meta.get("department_ids") or []
    department_ids: list[int] = []
    if isinstance(raw_dept_ids, list):
        for x in raw_dept_ids:
            try:
                department_ids.append(int(x))
            except (TypeError, ValueError):
                continue
    if not department_ids and n.department_id is not None:
        department_ids = [int(n.department_id)]
    due_in_days = int(meta.get("due_in_days") or 7)
    program_type = str(meta.get("program_type") or "custom")
    return ProgramOut(
        id=int(n.id),
        title=n.title,
        type=program_type,
        audience=_fe_audience(n.audience),
        department_id=n.department_id,
        department_ids=department_ids,
        student_ids=student_ids,
        due_in_days=due_in_days,
        due_date=_event_date(n),
        status="active" if not n.deleted_at else "cancelled",
        delivery_status=getattr(n, "delivery_status", None) or "queued",
        recipients_estimated=int(recipients_estimated or 0),
        message=n.body or "",
        created_at=n.created_at,
        created_by=n.created_by,
        metadata=meta,
    )


def _default_message(*, title: str, program_type: str, due_in_days: int) -> str:
    label = program_type.replace("_", " ")
    return (
        f"Your campus assigned “{title}” ({label}). "
        f"Please complete it within {due_in_days} day(s)."
    )


async def create_program(
    db: AsyncSession,
    *,
    ctx: TenantContext,
    title: str,
    program_type: str,
    audience: str,
    department_id: int | None,
    department_ids: list[int] | None = None,
    student_ids: list[int],
    due_in_days: int,
    message: str | None = None,
) -> tuple[Notification, int]:
    fe_aud = (audience or "all").strip().lower()
    dept_ids: list[int] = []
    if department_ids:
        dept_ids = list(dict.fromkeys(int(x) for x in department_ids))
    elif department_id is not None:
        dept_ids = [int(department_id)]

    if fe_aud == "all":
        stored = NotificationAudience.ORG.value
        dept_id = None
        user_ids = None
        dept_ids = []
    elif fe_aud == "department":
        stored = NotificationAudience.DEPARTMENT.value
        if not dept_ids:
            raise ProgramError("Pick at least one department.")
        dept_id = dept_ids[0]
        user_ids = None
    elif fe_aud == "student":
        stored = NotificationAudience.USERS.value
        dept_id = department_id or (dept_ids[0] if dept_ids else None)
        user_ids = list(dict.fromkeys(int(x) for x in student_ids))
    else:
        raise ProgramError("audience must be all, department, or student.")

    if not ctx.sees_all_students:
        # HOD: force department scope to their branch
        if ctx.department_id is None:
            raise ProgramError("HOD account is not linked to a department.", status_code=403)
        if fe_aud == "all":
            stored = NotificationAudience.DEPARTMENT.value
            dept_id = ctx.department_id
            dept_ids = [int(ctx.department_id)]
            user_ids = None
        elif fe_aud == "department":
            allowed = {int(ctx.department_id)}
            if not dept_ids or any(d not in allowed for d in dept_ids):
                dept_ids = [int(ctx.department_id)]
            dept_id = dept_ids[0]
        elif fe_aud == "student":
            dept_id = ctx.department_id
            dept_ids = [int(ctx.department_id)]

    due = date.today() + timedelta(days=max(1, int(due_in_days or 7)))
    body = (message or "").strip() or _default_message(
        title=title.strip(),
        program_type=program_type,
        due_in_days=due_in_days,
    )
    meta: dict[str, Any] = {
        "program_type": program_type,
        "due_in_days": int(due_in_days or 7),
        "student_ids": user_ids or [],
        "department_ids": dept_ids,
        "source": "programs",
    }

    try:
        notif = await notif_service.create_notification(
            db,
            ctx=ctx,
            title=title.strip(),
            body=body,
            audience=stored,
            department_id=dept_id,
            department_ids=dept_ids or None,
            user_ids=user_ids,
            metadata_json=meta,
            kind=NotificationKind.PROGRAM.value,
            event_date=due,
        )
    except notif_service.NotificationError as exc:
        raise ProgramError(exc.message, status_code=exc.status_code) from exc

    return notif, len(notif.recipients or [])


async def list_programs(
    db: AsyncSession,
    *,
    ctx: TenantContext,
) -> tuple[list[ProgramOut], int]:
    stmt = (
        select(Notification)
        .where(Notification.organization_id == ctx.organization_id)
        .where(Notification.deleted_at.is_(None))
        .where(Notification.kind == NotificationKind.PROGRAM.value)
        .order_by(Notification.id.desc())
    )
    if not ctx.sees_all_students:
        if ctx.department_id is None:
            return [], 0
        # Branch programs: department-scoped or campus-wide (all students)
        stmt = stmt.where(
            or_(
                Notification.audience == NotificationAudience.ORG.value,
                Notification.department_id == ctx.department_id,
            )
        )

    items = list((await db.execute(stmt)).scalars().unique().all())
    if not ctx.sees_all_students and ctx.department_id is not None:
        hod_dept = int(ctx.department_id)
        filtered: list[Notification] = []
        for n in items:
            if n.audience == NotificationAudience.ORG.value:
                filtered.append(n)
                continue
            meta = n.metadata_json if isinstance(n.metadata_json, dict) else {}
            raw = meta.get("department_ids") or []
            dept_ids: list[int] = []
            if isinstance(raw, list):
                for x in raw:
                    try:
                        dept_ids.append(int(x))
                    except (TypeError, ValueError):
                        continue
            if not dept_ids and n.department_id is not None:
                dept_ids = [int(n.department_id)]
            if hod_dept in dept_ids or n.department_id == hod_dept:
                filtered.append(n)
        items = filtered

    ids = [int(n.id) for n in items]
    counts: dict[int, int] = {}
    if ids:
        count_rows = await db.execute(
            select(NotificationRecipient.notification_id, func.count())
            .where(NotificationRecipient.notification_id.in_(ids))
            .group_by(NotificationRecipient.notification_id)
        )
        counts = {
            int(nid): int(cnt or 0)
            for nid, cnt in count_rows.all()
            if nid is not None
        }

    programs = [
        notification_to_program(n, recipients_estimated=counts.get(int(n.id), 0))
        for n in items
    ]
    return programs, len(programs)


async def delete_program(
    db: AsyncSession,
    *,
    ctx: TenantContext,
    program_id: int,
) -> Notification:
    try:
        notif = await notif_service.get_notification(db, program_id)
    except notif_service.NotificationError as exc:
        raise ProgramError(exc.message, status_code=exc.status_code) from exc

    if notif.organization_id != ctx.organization_id:
        raise ProgramError("Not in your organization.", status_code=403)
    if notif.kind != NotificationKind.PROGRAM.value:
        raise ProgramError("Not a program assignment.", status_code=400)
    if not ctx.sees_all_students:
        if ctx.department_id is None or (
            notif.audience != NotificationAudience.ORG.value
            and notif.department_id != ctx.department_id
        ):
            raise ProgramError("Cannot remove programs outside your department.", status_code=403)

    try:
        return await notif_service.soft_delete_notification(db, program_id)
    except notif_service.NotificationError as exc:
        raise ProgramError(exc.message, status_code=exc.status_code) from exc

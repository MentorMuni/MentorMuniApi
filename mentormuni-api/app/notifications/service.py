"""Notification service — create + fan-out recipients + campus email queue."""

from __future__ import annotations

import logging
from datetime import date, datetime, time, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.common.audit import write_audit
from app.common.database.session import async_session_factory
from app.common.email import send_simple_email
from app.common.email.exceptions import EmailError
from app.common.tenant.context import TenantContext
from app.models.enums import (
    NotificationAudience,
    NotificationDeliveryStatus,
    NotificationKind,
    NotificationRecipientStatus,
    NotificationStatus,
    RoleCode,
    UserStatus,
)
from app.models.notification import Notification
from app.models.notification_recipient import NotificationRecipient
from app.models.role import Role
from app.models.user import User

logger = logging.getLogger(__name__)

# FE audience ↔ stored audience
_FE_TO_STORED = {
    "all": NotificationAudience.ORG.value,
    "department": NotificationAudience.DEPARTMENT.value,
    "hods": NotificationAudience.HODS.value,
}
_STORED_TO_FE = {
    NotificationAudience.ORG.value: "all",
    NotificationAudience.DEPARTMENT.value: "department",
    NotificationAudience.HODS.value: "hods",
    NotificationAudience.USERS.value: "all",
}


class NotificationError(Exception):
    def __init__(self, message: str, *, status_code: int = 400) -> None:
        super().__init__(message)
        self.message = message
        self.status_code = status_code


def fe_audience(stored: str) -> str:
    return _STORED_TO_FE.get(stored, "all")


def stored_audience(fe: str) -> str:
    return _FE_TO_STORED.get(fe.lower().strip(), NotificationAudience.ORG.value)


async def _resolve_recipient_ids(
    db: AsyncSession,
    *,
    organization_id: int,
    audience: str,
    department_id: int | None,
    department_ids: list[int] | None = None,
    user_ids: list[int] | None = None,
) -> list[int]:
    if audience == NotificationAudience.USERS.value:
        return list(dict.fromkeys(user_ids or []))

    if audience == NotificationAudience.HODS.value:
        stmt = (
            select(User.id)
            .join(Role, User.role_id == Role.id)
            .where(User.organization_id == organization_id)
            .where(User.deleted_at.is_(None))
            .where(User.status.in_([UserStatus.ACTIVE.value, UserStatus.INVITED.value]))
            .where(Role.role_code == RoleCode.DEPARTMENT_ADMIN.value)
        )
        return list((await db.execute(stmt)).scalars().all())

    stmt = (
        select(User.id)
        .join(Role, User.role_id == Role.id)
        .where(User.organization_id == organization_id)
        .where(User.deleted_at.is_(None))
        .where(User.status == UserStatus.ACTIVE.value)
        .where(Role.role_code == RoleCode.STUDENT.value)
    )
    if audience == NotificationAudience.DEPARTMENT.value:
        dept_ids = list(dict.fromkeys(department_ids or []))
        if not dept_ids and department_id is not None:
            dept_ids = [int(department_id)]
        if not dept_ids:
            raise NotificationError("department_id or department_ids required for DEPARTMENT audience.")
        stmt = stmt.where(User.department_id.in_(dept_ids))
    return list((await db.execute(stmt)).scalars().all())


def _normalize_department_ids(
    department_id: int | None,
    department_ids: list[int] | None,
) -> list[int]:
    out: list[int] = []
    if department_ids:
        for raw in department_ids:
            try:
                out.append(int(raw))
            except (TypeError, ValueError):
                continue
    elif department_id is not None:
        out.append(int(department_id))
    return list(dict.fromkeys(out))


def _assert_department_scope(
    ctx: TenantContext,
    *,
    audience: str,
    department_ids: list[int],
) -> None:
    if ctx.sees_all_students:
        return
    if audience != NotificationAudience.DEPARTMENT.value:
        raise NotificationError("HOD can only send department-scoped notifications.", status_code=403)
    if ctx.department_id is None:
        raise NotificationError("HOD account is not linked to a department.", status_code=403)
    allowed = {int(ctx.department_id)}
    bad = [d for d in department_ids if d not in allowed]
    if bad:
        raise NotificationError("HOD can only notify their own department.", status_code=403)


def assert_can_manage_notification(ctx: TenantContext, notif: Notification) -> None:
    """TPO may cancel any org notice; HOD only department notices for their branch."""
    if ctx.sees_all_students:
        return
    if notif.audience != NotificationAudience.DEPARTMENT.value:
        raise NotificationError("HOD can only manage department notifications.", status_code=403)
    if ctx.department_id is None:
        raise NotificationError("HOD account is not linked to a department.", status_code=403)
    dept_ids = _department_ids_from_row(notif)
    if int(ctx.department_id) not in dept_ids:
        raise NotificationError("HOD can only manage notifications for their department.", status_code=403)


async def create_notification(
    db: AsyncSession,
    *,
    ctx: TenantContext,
    title: str,
    body: str,
    audience: str,
    department_id: int | None = None,
    department_ids: list[int] | None = None,
    user_ids: list[int] | None = None,
    metadata_json: dict | None = None,
    kind: str = NotificationKind.ANNOUNCEMENT.value,
    event_date: date | datetime | None = None,
    delivery_status: str = NotificationDeliveryStatus.QUEUED.value,
) -> Notification:
    dept_ids = _normalize_department_ids(department_id, department_ids)
    if audience == NotificationAudience.DEPARTMENT.value and not dept_ids:
        raise NotificationError("department_id or department_ids required for DEPARTMENT audience.")
    if audience == NotificationAudience.USERS.value and not user_ids:
        raise NotificationError("user_ids required for USERS audience.")

    if not ctx.sees_all_students and audience == NotificationAudience.ORG.value:
        raise NotificationError("Only TPO can send org-wide notifications.", status_code=403)
    if not ctx.sees_all_students and audience == NotificationAudience.HODS.value:
        raise NotificationError("Only TPO / Org Admin can notify HODs.", status_code=403)
    if audience == NotificationAudience.DEPARTMENT.value:
        _assert_department_scope(ctx, audience=audience, department_ids=dept_ids)

    meta = dict(metadata_json or {})
    if dept_ids:
        meta["department_ids"] = dept_ids
    primary_dept = dept_ids[0] if dept_ids else department_id

    event_dt: datetime | None = None
    if isinstance(event_date, datetime):
        event_dt = event_date
    elif isinstance(event_date, date):
        event_dt = datetime.combine(event_date, time.min, tzinfo=timezone.utc)

    kind_norm = (kind or NotificationKind.ANNOUNCEMENT.value).strip().lower()
    try:
        kind_norm = NotificationKind(kind_norm).value
    except ValueError as exc:
        raise NotificationError(
            f"kind must be one of: {', '.join(k.value for k in NotificationKind)}"
        ) from exc

    notif = Notification(
        organization_id=ctx.organization_id,
        created_by=ctx.user_id,
        title=title.strip(),
        body=body.strip(),
        kind=kind_norm,
        event_date=event_dt,
        audience=audience,
        department_id=primary_dept,
        status=NotificationStatus.ACTIVE.value,
        delivery_status=delivery_status,
        metadata_json=meta or None,
    )
    db.add(notif)
    await db.flush()

    recipient_user_ids = await _resolve_recipient_ids(
        db,
        organization_id=ctx.organization_id,
        audience=audience,
        department_id=primary_dept,
        department_ids=dept_ids,
        user_ids=user_ids,
    )

    for uid in recipient_user_ids:
        db.add(
            NotificationRecipient(
                notification_id=notif.id,
                user_id=uid,
                status=NotificationRecipientStatus.UNREAD.value,
            )
        )
    await db.flush()

    await write_audit(
        db,
        organization_id=ctx.organization_id,
        actor_user_id=ctx.user_id,
        action="NOTIFICATION_CREATE",
        entity_type="notification",
        entity_id=notif.id,
        payload={
            "audience": audience,
            "kind": kind_norm,
            "recipients": len(recipient_user_ids),
            "delivery_status": delivery_status,
        },
    )

    result = await db.execute(
        select(Notification)
        .where(Notification.id == notif.id)
        .options(selectinload(Notification.recipients))
    )
    return result.scalar_one()


async def create_campus_notification(
    db: AsyncSession,
    *,
    ctx: TenantContext,
    kind: str,
    title: str,
    message: str,
    audience: str,
    department_id: int | None = None,
    department_ids: list[int] | None = None,
    event_date: date | None = None,
) -> tuple[Notification, int]:
    """Campus notify — TPO (all audiences) or HOD (department audience only)."""
    fe_aud = (audience or "all").strip().lower()
    if not ctx.sees_all_students and fe_aud != "department":
        raise NotificationError(
            "HOD can only notify students in their department.",
            status_code=403,
        )
    stored = stored_audience(fe_aud)
    dept_ids = _normalize_department_ids(department_id, department_ids)
    notif = await create_notification(
        db,
        ctx=ctx,
        title=title,
        body=message,
        audience=stored,
        department_id=dept_ids[0] if dept_ids else department_id,
        department_ids=dept_ids or None,
        kind=kind,
        event_date=event_date,
        delivery_status=NotificationDeliveryStatus.QUEUED.value,
    )
    return notif, len(notif.recipients or [])


def _department_ids_from_row(notification: Notification) -> list[int]:
    meta = notification.metadata_json if isinstance(notification.metadata_json, dict) else {}
    raw = meta.get("department_ids")
    if isinstance(raw, list) and raw:
        out: list[int] = []
        for x in raw:
            try:
                out.append(int(x))
            except (TypeError, ValueError):
                continue
        if out:
            return list(dict.fromkeys(out))
    if notification.department_id is not None:
        return [int(notification.department_id)]
    return []


async def list_notifications(
    db: AsyncSession,
    *,
    organization_id: int,
    ctx: TenantContext | None = None,
) -> tuple[list[Notification], int, dict[int, int]]:
    """
    List campus notifications without loading every recipient row.
    Returns (items, total, recipient_counts_by_notification_id).
    HOD sees only department-scoped notices for their branch.
    """
    stmt = (
        select(Notification)
        .where(Notification.organization_id == organization_id)
        .where(Notification.deleted_at.is_(None))
        .order_by(Notification.id.desc())
    )
    items = list((await db.execute(stmt)).scalars().unique().all())

    if ctx is not None and not ctx.sees_all_students and ctx.department_id is not None:
        hod_dept = int(ctx.department_id)
        scoped: list[Notification] = []
        for n in items:
            if n.audience != NotificationAudience.DEPARTMENT.value:
                continue
            dept_ids = _department_ids_from_row(n)
            if hod_dept in dept_ids:
                scoped.append(n)
        items = scoped
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
    return items, len(items), counts


async def get_notification(db: AsyncSession, notification_id: int) -> Notification:
    result = await db.execute(
        select(Notification)
        .where(Notification.id == notification_id)
        .where(Notification.deleted_at.is_(None))
        .options(selectinload(Notification.recipients))
    )
    notif = result.scalar_one_or_none()
    if notif is None:
        raise NotificationError("Notification not found.", status_code=404)
    return notif


async def update_notification(
    db: AsyncSession,
    notification_id: int,
    **fields: object,
) -> Notification:
    notif = await get_notification(db, notification_id)
    for key, value in fields.items():
        if value is None:
            continue
        setattr(notif, key, value)
    await db.flush()
    return await get_notification(db, notification_id)


async def soft_delete_notification(db: AsyncSession, notification_id: int) -> Notification:
    notif = await get_notification(db, notification_id)
    notif.deleted_at = datetime.now(timezone.utc)
    notif.status = NotificationStatus.INACTIVE.value
    notif.delivery_status = NotificationDeliveryStatus.CANCELLED.value
    await db.flush()
    return notif


async def inbox_for_user(db: AsyncSession, *, user_id: int) -> list[NotificationRecipient]:
    result = await db.execute(
        select(NotificationRecipient)
        .join(Notification, NotificationRecipient.notification_id == Notification.id)
        .where(NotificationRecipient.user_id == user_id)
        .where(Notification.deleted_at.is_(None))
        .where(Notification.status == NotificationStatus.ACTIVE.value)
        .options(selectinload(NotificationRecipient.notification))
        .order_by(NotificationRecipient.id.desc())
    )
    return list(result.scalars().unique().all())


async def mark_read(
    db: AsyncSession,
    *,
    notification_id: int,
    user_id: int,
) -> NotificationRecipient:
    result = await db.execute(
        select(NotificationRecipient).where(
            NotificationRecipient.notification_id == notification_id,
            NotificationRecipient.user_id == user_id,
        )
    )
    row = result.scalar_one_or_none()
    if row is None:
        raise NotificationError("Inbox item not found.", status_code=404)
    row.status = NotificationRecipientStatus.READ.value
    row.read_at = datetime.now(timezone.utc)
    await db.flush()
    return row


async def deliver_notification_emails(notification_id: int) -> None:
    """Background email fan-out. Updates delivery_status; never blocks the create API."""
    factory = async_session_factory()
    async with factory() as db:
        try:
            result = await db.execute(
                select(Notification)
                .where(Notification.id == notification_id)
                .options(selectinload(Notification.recipients))
            )
            notif = result.scalar_one_or_none()
            if notif is None or notif.deleted_at is not None:
                return
            if notif.delivery_status == NotificationDeliveryStatus.CANCELLED.value:
                return

            notif.delivery_status = NotificationDeliveryStatus.SENDING.value
            await db.commit()

            recipient_ids = [r.user_id for r in (notif.recipients or [])]
            if not recipient_ids:
                notif.delivery_status = NotificationDeliveryStatus.SENT.value
                await db.commit()
                return

            users_result = await db.execute(
                select(User).where(User.id.in_(recipient_ids)).where(User.deleted_at.is_(None))
            )
            users = list(users_result.scalars().all())

            kind_label = (notif.kind or "announcement").capitalize()
            date_line = ""
            if notif.event_date:
                date_line = f"\nDate: {notif.event_date.date().isoformat()}"

            subject = f"[MentorMuni] {kind_label}: {notif.title}"
            sent = 0
            failed = 0
            for user in users:
                if not user.email:
                    continue
                text = (
                    f"Hi {user.first_name or 'there'},\n\n"
                    f"{notif.title}\n"
                    f"{date_line}\n\n"
                    f"{notif.body}\n\n"
                    f"— MentorMuni Campus"
                )
                try:
                    result_email = await send_simple_email(
                        to_email=user.email,
                        to_name=f"{user.first_name} {user.last_name}".strip() or None,
                        subject=subject,
                        text_body=text,
                    )
                    if result_email.sent or result_email.skipped:
                        sent += 1
                    else:
                        failed += 1
                except EmailError as exc:
                    failed += 1
                    logger.warning(
                        "notification_email_failed notification_id=%s user_id=%s err=%s",
                        notification_id,
                        user.id,
                        exc,
                    )
                except Exception as exc:
                    failed += 1
                    logger.warning(
                        "notification_email_unexpected notification_id=%s user_id=%s err=%s",
                        notification_id,
                        user.id,
                        exc,
                    )

            await db.refresh(notif)
            if notif.delivery_status == NotificationDeliveryStatus.CANCELLED.value:
                await db.commit()
                return
            if failed == 0:
                notif.delivery_status = NotificationDeliveryStatus.SENT.value
            elif sent == 0:
                notif.delivery_status = NotificationDeliveryStatus.FAILED.value
            else:
                notif.delivery_status = NotificationDeliveryStatus.PARTIAL.value
            await db.commit()
            logger.info(
                "notification_delivery_done id=%s sent=%s failed=%s status=%s",
                notification_id,
                sent,
                failed,
                notif.delivery_status,
            )
        except Exception:
            logger.exception("notification_delivery_crashed id=%s", notification_id)
            try:
                await db.rollback()
                n = await db.get(Notification, notification_id)
                if n is not None:
                    n.delivery_status = NotificationDeliveryStatus.FAILED.value
                    await db.commit()
            except Exception:
                logger.exception(
                    "notification_delivery_status_update_failed id=%s", notification_id
                )

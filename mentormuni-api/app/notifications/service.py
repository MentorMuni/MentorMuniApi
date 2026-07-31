"""Notification service — create + fan-out recipients."""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.common.audit import write_audit
from app.common.tenant.context import TenantContext
from app.models.enums import (
    NotificationAudience,
    NotificationRecipientStatus,
    NotificationStatus,
    RoleCode,
    UserStatus,
)
from app.models.notification import Notification
from app.models.notification_recipient import NotificationRecipient
from app.models.role import Role
from app.models.user import User


class NotificationError(Exception):
    def __init__(self, message: str, *, status_code: int = 400) -> None:
        super().__init__(message)
        self.message = message
        self.status_code = status_code


async def create_notification(
    db: AsyncSession,
    *,
    ctx: TenantContext,
    title: str,
    body: str,
    audience: str,
    department_id: int | None = None,
    user_ids: list[int] | None = None,
    metadata_json: dict | None = None,
) -> Notification:
    if audience == NotificationAudience.DEPARTMENT.value and department_id is None:
        raise NotificationError("department_id required for DEPARTMENT audience.")
    if audience == NotificationAudience.USERS.value and not user_ids:
        raise NotificationError("user_ids required for USERS audience.")

    if not ctx.sees_all_students and audience == NotificationAudience.ORG.value:
        raise NotificationError("Only TPO can send org-wide notifications.", status_code=403)
    if (
        not ctx.sees_all_students
        and audience == NotificationAudience.DEPARTMENT.value
        and department_id != ctx.department_id
    ):
        raise NotificationError("HOD can only notify their own department.", status_code=403)

    notif = Notification(
        organization_id=ctx.organization_id,
        created_by=ctx.user_id,
        title=title.strip(),
        body=body.strip(),
        audience=audience,
        department_id=department_id,
        status=NotificationStatus.ACTIVE.value,
        metadata_json=metadata_json,
    )
    db.add(notif)
    await db.flush()

    recipient_user_ids: list[int] = []
    if audience == NotificationAudience.USERS.value:
        recipient_user_ids = list(dict.fromkeys(user_ids or []))
    else:
        stmt = (
            select(User.id)
            .join(Role, User.role_id == Role.id)
            .where(User.organization_id == ctx.organization_id)
            .where(User.deleted_at.is_(None))
            .where(User.status == UserStatus.ACTIVE.value)
            .where(Role.role_code == RoleCode.STUDENT.value)
        )
        if audience == NotificationAudience.DEPARTMENT.value:
            stmt = stmt.where(User.department_id == department_id)
        recipient_user_ids = list((await db.execute(stmt)).scalars().all())

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
        payload={"audience": audience, "recipients": len(recipient_user_ids)},
    )

    result = await db.execute(
        select(Notification)
        .where(Notification.id == notif.id)
        .options(selectinload(Notification.recipients))
    )
    return result.scalar_one()


async def list_notifications(
    db: AsyncSession,
    *,
    organization_id: int,
) -> tuple[list[Notification], int]:
    stmt = (
        select(Notification)
        .where(Notification.organization_id == organization_id)
        .where(Notification.deleted_at.is_(None))
        .options(selectinload(Notification.recipients))
        .order_by(Notification.id.desc())
    )
    items = list((await db.execute(stmt)).scalars().unique().all())
    return items, len(items)


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

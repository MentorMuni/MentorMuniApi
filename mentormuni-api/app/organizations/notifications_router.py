"""
Campus notifications — TPO (all audiences) and HOD (department only).

POST   /organizations/notifications
GET    /organizations/notifications
DELETE /organizations/notifications/{id}
"""

from __future__ import annotations

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.deps import get_db, require_api_key
from app.common.tenant.context import TenantContext
from app.notifications import service as notif_service
from app.notifications.campus_schemas import (
    CampusNotificationCreate,
    CampusNotificationCreateResponse,
    CampusNotificationDeleteResponse,
    CampusNotificationItem,
    CampusNotificationListResponse,
)
from app.organizations.campus_notifications_access import require_campus_notifications

router = APIRouter(
    prefix="/organizations/notifications",
    tags=["Org Notifications"],
    dependencies=[Depends(require_api_key)],
)

_campus_notify = require_campus_notifications()


def _event_date(n) -> object:
    if n.event_date is None:
        return None
    return n.event_date.date() if hasattr(n.event_date, "date") else n.event_date


def _department_ids_from_notification(n) -> list[int]:
    meta = n.metadata_json if isinstance(n.metadata_json, dict) else {}
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
    if n.department_id is not None:
        return [int(n.department_id)]
    return []


def _to_item(n, *, recipients_estimated: int = 0) -> CampusNotificationItem:
    dept_ids = _department_ids_from_notification(n)
    return CampusNotificationItem(
        id=n.id,
        kind=getattr(n, "kind", None) or "announcement",
        title=n.title,
        message=n.body,
        date=_event_date(n),
        audience=notif_service.fe_audience(n.audience),
        department_id=n.department_id,
        department_ids=dept_ids,
        created_at=n.created_at,
        delivery_status=getattr(n, "delivery_status", None) or "queued",
        created_by=n.created_by,
        recipients_estimated=int(recipients_estimated or 0),
    )


@router.post("", response_model=CampusNotificationCreateResponse, status_code=201)
async def create_campus_notification(
    body: CampusNotificationCreate,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    ctx: TenantContext = Depends(_campus_notify),
) -> CampusNotificationCreateResponse:
    try:
        notif, count = await notif_service.create_campus_notification(
            db,
            ctx=ctx,
            kind=body.kind,
            title=body.title,
            message=body.message,
            audience=body.audience,
            department_id=body.department_id,
            department_ids=body.department_ids,
            event_date=body.date,
        )
    except notif_service.NotificationError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc

    background_tasks.add_task(notif_service.deliver_notification_emails, notif.id)

    return CampusNotificationCreateResponse(
        id=notif.id,
        delivery_status=getattr(notif, "delivery_status", None) or "queued",
        recipients_estimated=count,
        message="Notification queued.",
    )


@router.get("", response_model=CampusNotificationListResponse)
async def list_campus_notifications(
    db: AsyncSession = Depends(get_db),
    ctx: TenantContext = Depends(_campus_notify),
) -> CampusNotificationListResponse:
    items, total, recipient_counts = await notif_service.list_notifications(
        db, organization_id=ctx.organization_id, ctx=ctx
    )
    return CampusNotificationListResponse(
        items=[
            _to_item(n, recipients_estimated=recipient_counts.get(int(n.id), 0))
            for n in items
        ],
        total=total,
    )


@router.delete("/{notification_id}", response_model=CampusNotificationDeleteResponse)
async def delete_campus_notification(
    notification_id: int,
    db: AsyncSession = Depends(get_db),
    ctx: TenantContext = Depends(_campus_notify),
) -> CampusNotificationDeleteResponse:
    try:
        notif = await notif_service.get_notification(db, notification_id)
        if notif.organization_id != ctx.organization_id:
            raise HTTPException(status_code=403, detail="Not in your organization.")
        notif_service.assert_can_manage_notification(ctx, notif)
        notif = await notif_service.soft_delete_notification(db, notification_id)
    except notif_service.NotificationError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc
    return CampusNotificationDeleteResponse(
        id=notif.id,
        delivery_status=getattr(notif, "delivery_status", None) or "cancelled",
        message="Notification cancelled.",
    )

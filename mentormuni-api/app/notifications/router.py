"""
Notification routes.

POST   /notifications
GET    /notifications
GET    /notifications/inbox
PUT    /notifications/{id}
DELETE /notifications/{id}
PUT    /notifications/{id}/read
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.authz import require_permission
from app.common.deps import get_db, require_api_key
from app.common.tenant.context import TenantContext
from app.common.tenant.deps import get_tenant_context
from app.notifications import service as notif_service
from app.notifications.schemas import (
    InboxItem,
    NotificationCreate,
    NotificationListResponse,
    NotificationResponse,
    NotificationUpdate,
)

router = APIRouter(
    prefix="/notifications",
    tags=["Notifications"],
    dependencies=[Depends(require_api_key)],
)


def _to_response(n) -> NotificationResponse:
    return NotificationResponse(
        id=n.id,
        organization_id=n.organization_id,
        created_by=n.created_by,
        title=n.title,
        body=n.body,
        audience=n.audience,
        department_id=n.department_id,
        status=n.status,
        metadata_json=n.metadata_json,
        created_at=n.created_at,
        recipient_count=len(n.recipients) if n.recipients is not None else 0,
    )


@router.post("", response_model=NotificationResponse, status_code=201)
async def create_notification(
    body: NotificationCreate,
    db: AsyncSession = Depends(get_db),
    ctx: TenantContext = Depends(require_permission("SEND_NOTIFICATION")),
) -> NotificationResponse:
    try:
        notif = await notif_service.create_notification(
            db,
            ctx=ctx,
            title=body.title,
            body=body.body,
            audience=body.audience,
            department_id=body.department_id,
            user_ids=body.user_ids,
            metadata_json=body.metadata_json,
        )
    except notif_service.NotificationError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc
    return _to_response(notif)


@router.get("", response_model=NotificationListResponse)
async def list_notifications(
    db: AsyncSession = Depends(get_db),
    ctx: TenantContext = Depends(require_permission("SEND_NOTIFICATION", "VIEW_SELF")),
) -> NotificationListResponse:
    # Staff with SEND_NOTIFICATION see org list; students use /inbox
    if not ctx.has_permission("SEND_NOTIFICATION"):
        raise HTTPException(
            status_code=403,
            detail="Use GET /notifications/inbox for your messages.",
        )
    items, total = await notif_service.list_notifications(
        db, organization_id=ctx.organization_id
    )
    return NotificationListResponse(items=[_to_response(n) for n in items], total=total)


@router.get("/inbox", response_model=list[InboxItem])
async def my_inbox(
    db: AsyncSession = Depends(get_db),
    ctx: TenantContext = Depends(get_tenant_context),
) -> list[InboxItem]:
    rows = await notif_service.inbox_for_user(db, user_id=ctx.user_id)
    return [
        InboxItem(
            notification_id=r.notification_id,
            title=r.notification.title,
            body=r.notification.body,
            status=r.status,
            read_at=r.read_at,
            created_at=r.notification.created_at,
        )
        for r in rows
    ]


@router.put("/{notification_id}", response_model=NotificationResponse)
async def update_notification(
    notification_id: int,
    body: NotificationUpdate,
    db: AsyncSession = Depends(get_db),
    ctx: TenantContext = Depends(require_permission("SEND_NOTIFICATION")),
) -> NotificationResponse:
    try:
        notif = await notif_service.get_notification(db, notification_id)
        if notif.organization_id != ctx.organization_id:
            raise HTTPException(status_code=403, detail="Not in your organization.")
        notif = await notif_service.update_notification(
            db, notification_id, **body.model_dump(exclude_unset=True)
        )
    except notif_service.NotificationError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc
    return _to_response(notif)


@router.delete("/{notification_id}", response_model=NotificationResponse)
async def delete_notification(
    notification_id: int,
    db: AsyncSession = Depends(get_db),
    ctx: TenantContext = Depends(require_permission("SEND_NOTIFICATION")),
) -> NotificationResponse:
    try:
        notif = await notif_service.get_notification(db, notification_id)
        if notif.organization_id != ctx.organization_id:
            raise HTTPException(status_code=403, detail="Not in your organization.")
        notif = await notif_service.soft_delete_notification(db, notification_id)
    except notif_service.NotificationError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc
    return _to_response(notif)


@router.put("/{notification_id}/read", response_model=InboxItem)
async def mark_notification_read(
    notification_id: int,
    db: AsyncSession = Depends(get_db),
    ctx: TenantContext = Depends(get_tenant_context),
) -> InboxItem:
    try:
        row = await notif_service.mark_read(
            db, notification_id=notification_id, user_id=ctx.user_id
        )
        notif = await notif_service.get_notification(db, notification_id)
    except notif_service.NotificationError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc
    return InboxItem(
        notification_id=row.notification_id,
        title=notif.title,
        body=notif.body,
        status=row.status,
        read_at=row.read_at,
        created_at=notif.created_at,
    )

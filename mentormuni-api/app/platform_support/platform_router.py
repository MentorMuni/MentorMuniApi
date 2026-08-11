"""MentorMuni Support Inbox — no reporter names or emails."""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import PlatformRole
from app.models.platform_user import PlatformUser
from app.platform.deps import get_current_platform_user, get_db, require_api_key, require_platform_roles
from app.platform_support import service as svc
from app.platform_support.schemas import (
    ReplyCreateIn,
    TicketDetailOut,
    TicketListItemOut,
    TicketListOut,
)

router = APIRouter(
    prefix="/platform/support",
    tags=["Platform Support Inbox"],
    dependencies=[Depends(require_api_key)],
)


def _http(exc: svc.SupportError) -> HTTPException:
    return HTTPException(status_code=exc.status_code, detail=exc.message)


def _staff_user():
    return require_platform_roles(
        PlatformRole.PLATFORM_ADMIN.value,
        PlatformRole.SUPPORT.value,
        PlatformRole.OPERATIONS.value,
    )


@router.get("/tickets", response_model=TicketListOut)
async def list_tickets(
    status: Optional[str] = Query(default=None),
    source_portal: Optional[str] = Query(default=None),
    organization_id: Optional[int] = Query(default=None),
    db: AsyncSession = Depends(get_db),
    _user: PlatformUser = Depends(_staff_user()),
) -> TicketListOut:
    rows = await svc.list_platform_tickets(
        db,
        status=status,
        source_portal=source_portal,
        organization_id=organization_id,
    )
    items = [
        TicketListItemOut.model_validate(svc._ticket_preview(ticket, reply_count))
        for ticket, reply_count in rows
    ]
    return TicketListOut(items=items, total=len(items))


@router.get("/tickets/{ticket_id}", response_model=TicketDetailOut)
async def get_ticket(
    ticket_id: int,
    db: AsyncSession = Depends(get_db),
    _user: PlatformUser = Depends(_staff_user()),
) -> TicketDetailOut:
    try:
        ticket = await svc.get_ticket(db, ticket_id=ticket_id)
    except svc.SupportError as exc:
        raise _http(exc) from exc
    return TicketDetailOut.model_validate(svc.serialize_ticket(ticket, for_reporter=False))


@router.post("/tickets/{ticket_id}/replies", response_model=TicketDetailOut)
async def reply_ticket(
    ticket_id: int,
    body: ReplyCreateIn,
    db: AsyncSession = Depends(get_db),
    user: PlatformUser = Depends(_staff_user()),
) -> TicketDetailOut:
    try:
        ticket = await svc.get_ticket(db, ticket_id=ticket_id)
        ticket = await svc.add_reply(
            db,
            ticket=ticket,
            author_kind="platform",
            body=body.body,
            attachments=body.attachments,
            platform_user_id=user.id,
        )
    except svc.SupportError as exc:
        raise _http(exc) from exc
    return TicketDetailOut.model_validate(svc.serialize_ticket(ticket, for_reporter=False))


@router.post("/tickets/{ticket_id}/close", response_model=TicketDetailOut)
async def close_ticket(
    ticket_id: int,
    db: AsyncSession = Depends(get_db),
    _user: PlatformUser = Depends(_staff_user()),
) -> TicketDetailOut:
    try:
        ticket = await svc.get_ticket(db, ticket_id=ticket_id)
        ticket = await svc.close_ticket(db, ticket=ticket, closed_by_kind="platform")
    except svc.SupportError as exc:
        raise _http(exc) from exc
    return TicketDetailOut.model_validate(svc.serialize_ticket(ticket, for_reporter=False))

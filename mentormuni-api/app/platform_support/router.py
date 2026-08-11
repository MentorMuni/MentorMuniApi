"""Reporter Help Center APIs — student and organization portals."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.deps import get_current_active_user, get_db, require_api_key
from app.models.user import User
from app.platform_support import service as svc
from app.platform_support.schemas import (
    ReplyCreateIn,
    TicketCreateIn,
    TicketDetailOut,
    TicketListItemOut,
    TicketListOut,
)

router = APIRouter(
    prefix="/support",
    tags=["Help Center"],
    dependencies=[Depends(require_api_key)],
)


def _http(exc: svc.SupportError) -> HTTPException:
    return HTTPException(status_code=exc.status_code, detail=exc.message)


@router.post("/tickets", response_model=TicketDetailOut, status_code=201)
async def create_ticket(
    body: TicketCreateIn,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_active_user),
) -> TicketDetailOut:
    try:
        ticket = await svc.create_ticket(
            db,
            user=user,
            subject=body.subject,
            body=body.body,
            source_portal=body.source_portal,
            category=body.category,
            attachments=body.attachments,
        )
    except svc.SupportError as exc:
        raise _http(exc) from exc
    return TicketDetailOut.model_validate(svc.serialize_ticket(ticket, for_reporter=True))


@router.get("/tickets", response_model=TicketListOut)
async def list_tickets(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_active_user),
) -> TicketListOut:
    rows = await svc.list_my_tickets(db, user_id=user.id)
    items = [
        TicketListItemOut.model_validate(svc._ticket_preview(ticket, reply_count))
        for ticket, reply_count in rows
    ]
    return TicketListOut(items=items, total=len(items))


@router.get("/tickets/{ticket_id}", response_model=TicketDetailOut)
async def get_ticket(
    ticket_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_active_user),
) -> TicketDetailOut:
    try:
        ticket = await svc.get_my_ticket(db, ticket_id=ticket_id, user_id=user.id)
    except svc.SupportError as exc:
        raise _http(exc) from exc
    return TicketDetailOut.model_validate(svc.serialize_ticket(ticket, for_reporter=True))


@router.post("/tickets/{ticket_id}/replies", response_model=TicketDetailOut)
async def reply_ticket(
    ticket_id: int,
    body: ReplyCreateIn,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_active_user),
) -> TicketDetailOut:
    try:
        ticket = await svc.get_my_ticket(db, ticket_id=ticket_id, user_id=user.id)
        ticket = await svc.add_reply(
            db,
            ticket=ticket,
            author_kind="reporter",
            body=body.body,
            attachments=body.attachments,
            user_id=user.id,
        )
    except svc.SupportError as exc:
        raise _http(exc) from exc
    return TicketDetailOut.model_validate(svc.serialize_ticket(ticket, for_reporter=True))


@router.post("/tickets/{ticket_id}/close", response_model=TicketDetailOut)
async def close_ticket(
    ticket_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_active_user),
) -> TicketDetailOut:
    try:
        ticket = await svc.get_my_ticket(db, ticket_id=ticket_id, user_id=user.id)
        ticket = await svc.close_ticket(db, ticket=ticket, closed_by_kind="reporter")
    except svc.SupportError as exc:
        raise _http(exc) from exc
    return TicketDetailOut.model_validate(svc.serialize_ticket(ticket, for_reporter=True))

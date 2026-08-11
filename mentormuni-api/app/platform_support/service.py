"""Help Center tickets. Platform views never include reporter name or email."""

from __future__ import annotations

import base64
import binascii
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.enums import RoleCode, SupportCategory, SupportSourcePortal, SupportTicketStatus
from app.models.platform_support import PlatformSupportReply, PlatformSupportTicket
from app.models.platform_user import PlatformUser
from app.models.user import User

MAX_ATTACHMENTS = 3
MAX_ATTACHMENT_BYTES = 2 * 1024 * 1024
ALLOWED_CONTENT_TYPES = {"image/png", "image/jpeg", "image/jpg", "image/webp"}
ALLOWED_CATEGORIES = {c.value for c in SupportCategory}


class SupportError(Exception):
    def __init__(self, message: str, status_code: int = 400):
        super().__init__(message)
        self.message = message
        self.status_code = status_code


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def reporter_role_label(role_code: str) -> str:
    if role_code == RoleCode.STUDENT.value:
        return "Student"
    return "Campus staff"


def validate_source_portal(user: User, source_portal: str) -> str:
    portal = (source_portal or "").strip().lower()
    if portal not in {SupportSourcePortal.STUDENT.value, SupportSourcePortal.ORGANIZATION.value}:
        raise SupportError("Choose Student Portal or Organization Portal.")
    role = user.role.role_code if user.role else None
    if role == RoleCode.STUDENT.value and portal != SupportSourcePortal.STUDENT.value:
        raise SupportError("Student accounts can only send from the Student Portal.")
    if role in {RoleCode.ORG_ADMIN.value, RoleCode.DEPARTMENT_ADMIN.value} and portal != SupportSourcePortal.ORGANIZATION.value:
        raise SupportError("Campus accounts can only send from the Organization Portal.")
    return portal


def normalize_attachments(raw: list | None) -> list[dict]:
    items = list(raw or [])
    if len(items) > MAX_ATTACHMENTS:
        raise SupportError(f"Attach at most {MAX_ATTACHMENTS} images.")
    cleaned: list[dict] = []
    for item in items:
        filename = str(getattr(item, "filename", None) or item.get("filename") or "screenshot.png")[:200]
        content_type = str(
            getattr(item, "content_type", None) or item.get("content_type") or ""
        ).lower().strip()
        data = str(getattr(item, "data_base64", None) or item.get("data_base64") or "")
        if "," in data and data.strip().startswith("data:"):
            data = data.split(",", 1)[1]
        data = "".join(data.split())
        if content_type not in ALLOWED_CONTENT_TYPES:
            raise SupportError("Screenshots must be PNG, JPEG, or WebP.")
        try:
            decoded = base64.b64decode(data, validate=True)
        except (binascii.Error, ValueError) as exc:
            raise SupportError("One of the images could not be read.") from exc
        if len(decoded) > MAX_ATTACHMENT_BYTES:
            raise SupportError("Each image must be 2 MB or smaller.")
        if not decoded:
            raise SupportError("One of the images is empty.")
        cleaned.append(
            {
                "filename": filename or "screenshot.png",
                "content_type": "image/jpeg" if content_type == "image/jpg" else content_type,
                "data_base64": data,
            }
        )
    return cleaned


def _ticket_preview(ticket: PlatformSupportTicket, reply_count: int = 0) -> dict:
    return {
        "id": ticket.id,
        "subject": ticket.subject,
        "status": ticket.status,
        "category": ticket.category,
        "organization_id": ticket.organization_id,
        "organization_name": ticket.organization_name,
        "organization_code": ticket.organization_code,
        "source_portal": ticket.source_portal,
        "reporter_role_label": reporter_role_label(ticket.reporter_role_code),
        "reply_count": reply_count,
        "created_at": ticket.created_at,
        "updated_at": ticket.updated_at,
        "closed_at": ticket.closed_at,
    }


def serialize_reply(reply: PlatformSupportReply, *, for_reporter: bool) -> dict:
    if reply.author_kind == "platform":
        label = "MentorMuni Support"
    elif for_reporter:
        label = "You"
    else:
        label = "Reporter"
    attachments = []
    for item in reply.attachments_json or []:
        if not isinstance(item, dict):
            continue
        attachments.append(
            {
                "filename": item.get("filename") or "screenshot.png",
                "content_type": item.get("content_type") or "image/png",
                "data_base64": item.get("data_base64") or "",
            }
        )
    return {
        "id": reply.id,
        "author_kind": reply.author_kind,
        "author_label": label,
        "body": reply.body,
        "attachments": attachments,
        "created_at": reply.created_at,
    }


def serialize_ticket(ticket: PlatformSupportTicket, *, for_reporter: bool) -> dict:
    replies = list(ticket.replies or [])
    payload = _ticket_preview(ticket, reply_count=len(replies))
    payload["replies"] = [serialize_reply(r, for_reporter=for_reporter) for r in replies]
    return payload


async def create_ticket(
    db: AsyncSession,
    *,
    user: User,
    subject: str,
    body: str,
    source_portal: str,
    category: str,
    attachments: list | None,
) -> PlatformSupportTicket:
    portal = validate_source_portal(user, source_portal)
    cat = (category or SupportCategory.OTHER.value).strip().lower()
    if cat not in ALLOWED_CATEGORIES:
        cat = SupportCategory.OTHER.value
    org = user.organization
    if not org:
        raise SupportError("Your account is not linked to an organization.", 400)
    files = normalize_attachments(attachments)
    ticket = PlatformSupportTicket(
        organization_id=user.organization_id,
        organization_name=org.name,
        organization_code=org.code,
        source_portal=portal,
        reporter_user_id=user.id,
        reporter_role_code=user.role.role_code if user.role else "UNKNOWN",
        category=cat,
        subject=subject.strip(),
        status=SupportTicketStatus.OPEN.value,
    )
    db.add(ticket)
    await db.flush()
    reply = PlatformSupportReply(
        ticket_id=ticket.id,
        author_kind="reporter",
        author_user_id=user.id,
        body=body.strip(),
        attachments_json=files or None,
    )
    db.add(reply)
    await db.flush()
    return await get_ticket(db, ticket_id=ticket.id)


async def list_my_tickets(db: AsyncSession, *, user_id: int) -> list[tuple[PlatformSupportTicket, int]]:
    count_sq = (
        select(func.count(PlatformSupportReply.id))
        .where(PlatformSupportReply.ticket_id == PlatformSupportTicket.id)
        .correlate(PlatformSupportTicket)
        .scalar_subquery()
    )
    rows = (
        await db.execute(
            select(PlatformSupportTicket, count_sq)
            .where(PlatformSupportTicket.reporter_user_id == user_id)
            .order_by(PlatformSupportTicket.updated_at.desc())
        )
    ).all()
    return [(row[0], int(row[1] or 0)) for row in rows]


async def list_platform_tickets(
    db: AsyncSession,
    *,
    status: Optional[str] = None,
    source_portal: Optional[str] = None,
    organization_id: Optional[int] = None,
) -> list[tuple[PlatformSupportTicket, int]]:
    count_sq = (
        select(func.count(PlatformSupportReply.id))
        .where(PlatformSupportReply.ticket_id == PlatformSupportTicket.id)
        .correlate(PlatformSupportTicket)
        .scalar_subquery()
    )
    q = select(PlatformSupportTicket, count_sq)
    if status:
        q = q.where(PlatformSupportTicket.status == status)
    if source_portal:
        q = q.where(PlatformSupportTicket.source_portal == source_portal)
    if organization_id:
        q = q.where(PlatformSupportTicket.organization_id == organization_id)
    q = q.order_by(PlatformSupportTicket.updated_at.desc())
    rows = (await db.execute(q)).all()
    return [(row[0], int(row[1] or 0)) for row in rows]


async def get_ticket(db: AsyncSession, *, ticket_id: int) -> PlatformSupportTicket:
    ticket = (
        await db.execute(
            select(PlatformSupportTicket)
            .options(selectinload(PlatformSupportTicket.replies))
            .where(PlatformSupportTicket.id == ticket_id)
        )
    ).scalar_one_or_none()
    if not ticket:
        raise SupportError("Ticket not found.", 404)
    return ticket


async def get_my_ticket(db: AsyncSession, *, ticket_id: int, user_id: int) -> PlatformSupportTicket:
    ticket = await get_ticket(db, ticket_id=ticket_id)
    if ticket.reporter_user_id != user_id:
        raise SupportError("Ticket not found.", 404)
    return ticket


async def add_reply(
    db: AsyncSession,
    *,
    ticket: PlatformSupportTicket,
    author_kind: str,
    body: str,
    attachments: list | None,
    user_id: Optional[int] = None,
    platform_user_id: Optional[int] = None,
) -> PlatformSupportTicket:
    if ticket.status == SupportTicketStatus.CLOSED.value:
        raise SupportError("This ticket is closed.")
    files = normalize_attachments(attachments)
    db.add(
        PlatformSupportReply(
            ticket_id=ticket.id,
            author_kind=author_kind,
            author_user_id=user_id,
            author_platform_user_id=platform_user_id,
            body=body.strip(),
            attachments_json=files or None,
        )
    )
    if author_kind == "platform":
        ticket.status = SupportTicketStatus.WAITING_REPORTER.value
    else:
        ticket.status = SupportTicketStatus.WAITING_PLATFORM.value
    ticket.updated_at = utc_now()
    await db.flush()
    return await get_ticket(db, ticket_id=ticket.id)


async def close_ticket(
    db: AsyncSession,
    *,
    ticket: PlatformSupportTicket,
    closed_by_kind: str,
) -> PlatformSupportTicket:
    if ticket.status == SupportTicketStatus.CLOSED.value:
        return ticket
    ticket.status = SupportTicketStatus.CLOSED.value
    ticket.closed_at = utc_now()
    ticket.closed_by_kind = closed_by_kind
    ticket.updated_at = utc_now()
    await db.flush()
    return await get_ticket(db, ticket_id=ticket.id)


# Keep PlatformUser imported for type checkers / future author display.
_ = PlatformUser

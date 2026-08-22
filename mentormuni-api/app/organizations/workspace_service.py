"""Personal workspace notepad for Org Admins and HODs (per-user, not shared)."""

from __future__ import annotations

from datetime import date, datetime, timezone
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.tenant.context import TenantContext
from app.models.enums import RoleCode
from app.models.workspace_item import WorkspaceItem

CAMPUS_TZ = ZoneInfo("Asia/Kolkata")


class WorkspaceError(Exception):
    def __init__(self, message: str, *, status_code: int = 400) -> None:
        super().__init__(message)
        self.message = message
        self.status_code = status_code


def require_workspace_access(ctx: TenantContext) -> None:
    """Org Admin (TPO/Dean/Director) or HOD — personal notepad per user."""
    if ctx.role in (RoleCode.ORG_ADMIN.value, RoleCode.DEPARTMENT_ADMIN.value):
        return
    if ctx.sees_all_students:
        return
    raise WorkspaceError(
        "Only Org Admins and HODs can use My Workspace.",
        status_code=403,
    )


def _campus_today() -> date:
    return datetime.now(CAMPUS_TZ).date()


def _reject_past_due_date(due_date: date | None) -> None:
    """Reminders must be today or later (Asia/Kolkata calendar date)."""
    if due_date is None:
        return
    if due_date < _campus_today():
        raise WorkspaceError(
            "Due date cannot be in the past. Leave it blank for a note, or pick today or later.",
            status_code=422,
        )


async def list_items(db: AsyncSession, *, ctx: TenantContext) -> list[WorkspaceItem]:
    require_workspace_access(ctx)
    result = await db.execute(
        select(WorkspaceItem)
        .where(WorkspaceItem.user_id == ctx.user_id)
        .where(WorkspaceItem.deleted_at.is_(None))
        .order_by(WorkspaceItem.done.asc(), WorkspaceItem.id.desc())
    )
    return list(result.scalars().all())


async def create_item(
    db: AsyncSession,
    *,
    ctx: TenantContext,
    text: str,
    kind: str = "todo",
    due_date: date | None = None,
    done: bool = False,
) -> WorkspaceItem:
    require_workspace_access(ctx)
    _reject_past_due_date(due_date)
    item = WorkspaceItem(
        user_id=ctx.user_id,
        organization_id=ctx.organization_id,
        text=text.strip(),
        kind=kind,
        due_date=due_date,
        done=bool(done),
    )
    db.add(item)
    await db.flush()
    await db.refresh(item)
    return item


async def get_owned_item(
    db: AsyncSession,
    *,
    ctx: TenantContext,
    item_id: int,
) -> WorkspaceItem:
    require_workspace_access(ctx)
    result = await db.execute(
        select(WorkspaceItem)
        .where(WorkspaceItem.id == item_id)
        .where(WorkspaceItem.user_id == ctx.user_id)
        .where(WorkspaceItem.deleted_at.is_(None))
    )
    item = result.scalar_one_or_none()
    if item is None:
        raise WorkspaceError("Workspace item not found.", status_code=404)
    return item


async def update_item(
    db: AsyncSession,
    *,
    ctx: TenantContext,
    item_id: int,
    text: str | None = None,
    kind: str | None = None,
    due_date: date | None = None,
    clear_due_date: bool = False,
    done: bool | None = None,
) -> WorkspaceItem:
    item = await get_owned_item(db, ctx=ctx, item_id=item_id)
    if text is not None:
        item.text = text.strip()
    if kind is not None:
        item.kind = kind
    if clear_due_date:
        item.due_date = None
    elif due_date is not None:
        # Allow echoing an already-stored past date (edit text / mark done).
        if due_date != item.due_date:
            _reject_past_due_date(due_date)
        item.due_date = due_date
    if done is not None:
        item.done = bool(done)
    item.updated_at = datetime.now(timezone.utc)
    await db.flush()
    await db.refresh(item)
    return item


async def delete_item(
    db: AsyncSession,
    *,
    ctx: TenantContext,
    item_id: int,
) -> None:
    item = await get_owned_item(db, ctx=ctx, item_id=item_id)
    item.deleted_at = datetime.now(timezone.utc)
    item.updated_at = datetime.now(timezone.utc)
    await db.flush()

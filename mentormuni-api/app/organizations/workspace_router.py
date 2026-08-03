"""
My Workspace — private notepad for Org Admins and HODs.

GET    /organizations/workspace/items
POST   /organizations/workspace/items
PUT    /organizations/workspace/items/{id}
DELETE /organizations/workspace/items/{id}

Per authenticated user (not shared across admins in the same college).
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.deps import get_db, require_api_key
from app.common.tenant.context import TenantContext
from app.common.tenant.deps import get_tenant_context
from app.organizations import workspace_service as svc
from app.organizations.workspace_schemas import (
    WorkspaceItemCreate,
    WorkspaceItemListResponse,
    WorkspaceItemResponse,
    WorkspaceItemUpdate,
)

router = APIRouter(
    prefix="/organizations/workspace",
    tags=["Org Workspace"],
    dependencies=[Depends(require_api_key)],
)


def _to_response(item) -> WorkspaceItemResponse:
    return WorkspaceItemResponse.model_validate(item)


@router.get("/items", response_model=WorkspaceItemListResponse)
async def list_workspace_items(
    db: AsyncSession = Depends(get_db),
    ctx: TenantContext = Depends(get_tenant_context),
) -> WorkspaceItemListResponse:
    try:
        items = await svc.list_items(db, ctx=ctx)
    except svc.WorkspaceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc
    return WorkspaceItemListResponse(items=[_to_response(i) for i in items])


@router.post("/items", response_model=WorkspaceItemResponse, status_code=201)
async def create_workspace_item(
    body: WorkspaceItemCreate,
    db: AsyncSession = Depends(get_db),
    ctx: TenantContext = Depends(get_tenant_context),
) -> WorkspaceItemResponse:
    try:
        item = await svc.create_item(
            db,
            ctx=ctx,
            text=body.text,
            kind=body.kind,
            due_date=body.due_date,
            done=body.done,
        )
    except svc.WorkspaceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc
    return _to_response(item)


@router.put("/items/{item_id}", response_model=WorkspaceItemResponse)
async def update_workspace_item(
    item_id: int,
    body: WorkspaceItemUpdate,
    db: AsyncSession = Depends(get_db),
    ctx: TenantContext = Depends(get_tenant_context),
) -> WorkspaceItemResponse:
    data = body.model_dump(exclude_unset=True)
    # Explicit null due_date clears the date
    clear_due = "due_date" in data and data.get("due_date") is None
    try:
        item = await svc.update_item(
            db,
            ctx=ctx,
            item_id=item_id,
            text=data.get("text"),
            kind=data.get("kind"),
            due_date=data.get("due_date"),
            clear_due_date=clear_due,
            done=data.get("done"),
        )
    except svc.WorkspaceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc
    return _to_response(item)


@router.delete("/items/{item_id}", status_code=204)
async def delete_workspace_item(
    item_id: int,
    db: AsyncSession = Depends(get_db),
    ctx: TenantContext = Depends(get_tenant_context),
) -> Response:
    try:
        await svc.delete_item(db, ctx=ctx, item_id=item_id)
    except svc.WorkspaceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc
    return Response(status_code=204)

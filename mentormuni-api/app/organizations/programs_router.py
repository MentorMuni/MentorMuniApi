"""
Org Portal programs / assessment assignments.

POST   /organizations/programs
GET    /organizations/programs
DELETE /organizations/programs/{id}

Stored as notifications with kind=program so students receive inbox delivery.
Auth: TPO + HOD (ASSIGN_PROGRAM / SEND_NOTIFICATION).
"""

from __future__ import annotations

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.deps import get_db, require_api_key
from app.common.tenant.context import TenantContext
from app.notifications import service as notif_service
from app.organizations import programs_service as prog_service
from app.organizations.programs_access import require_programs_access
from app.organizations.programs_schemas import (
    ProgramCreateIn,
    ProgramCreateResponse,
    ProgramDeleteResponse,
    ProgramListResponse,
)

router = APIRouter(
    prefix="/organizations/programs",
    tags=["Organization Programs"],
    dependencies=[Depends(require_api_key)],
)

_programs_access = require_programs_access()


@router.post("", response_model=ProgramCreateResponse, status_code=201)
async def create_program(
    body: ProgramCreateIn,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    ctx: TenantContext = Depends(_programs_access),
) -> ProgramCreateResponse:
    try:
        notif, count = await prog_service.create_program(
            db,
            ctx=ctx,
            title=body.title,
            program_type=body.type,
            audience=body.audience,
            department_id=body.department_id,
            department_ids=body.department_ids,
            student_ids=body.student_ids,
            due_in_days=body.due_in_days,
            message=body.message,
        )
    except prog_service.ProgramError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc

    background_tasks.add_task(notif_service.deliver_notification_emails, notif.id)
    program = prog_service.notification_to_program(notif, recipients_estimated=count)
    return ProgramCreateResponse(
        program=program,
        message=f"Program assigned to ~{count} student(s).",
    )


@router.get("", response_model=ProgramListResponse)
async def list_programs(
    db: AsyncSession = Depends(get_db),
    ctx: TenantContext = Depends(_programs_access),
) -> ProgramListResponse:
    items, total = await prog_service.list_programs(db, ctx=ctx)
    return ProgramListResponse(items=items, total=total)


@router.delete("/{program_id}", response_model=ProgramDeleteResponse)
async def delete_program(
    program_id: int,
    db: AsyncSession = Depends(get_db),
    ctx: TenantContext = Depends(_programs_access),
) -> ProgramDeleteResponse:
    try:
        await prog_service.delete_program(db, ctx=ctx, program_id=program_id)
    except prog_service.ProgramError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc
    return ProgramDeleteResponse(id=program_id, message="Program removed.")

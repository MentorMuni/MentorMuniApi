"""
Org Portal students — FE contract under /organizations/students.

Roster · invite · import · approve/reject · patch · delete
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.authz import require_permission
from app.common.deps import get_db, require_api_key
from app.common.tenant.context import TenantContext
from app.organizations import students_service as svc
from app.organizations.students_schemas import (
    OrgInviteListResponse,
    OrgInviteResponse,
    OrgStudentListResponse,
    OrgStudentResponse,
    StudentApproveResponse,
    StudentDecisionRequest,
    StudentDeleteResponse,
    StudentImportRequest,
    StudentImportResult,
    StudentInviteRequest,
    StudentInviteResult,
    StudentManualCreate,
    StudentManualCreateResponse,
    StudentPatchRequest,
    StudentRejectResponse,
    StudentUpdateResponse,
)

router = APIRouter(
    prefix="/organizations/students",
    tags=["Organization Students"],
    dependencies=[Depends(require_api_key)],
)


@router.get("", response_model=OrgStudentListResponse)
async def list_students(
    department_id: int | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
    ctx: TenantContext = Depends(
        require_permission(
            "VIEW_ALL_STUDENTS",
            "VIEW_DEPARTMENT_STUDENTS",
            "UPLOAD_STUDENTS",
            "APPROVE_STUDENT",
        )
    ),
) -> OrgStudentListResponse:
    items, total = await svc.list_roster(db, ctx, department_id=department_id)
    return OrgStudentListResponse(
        items=[OrgStudentResponse.model_validate(i) for i in items],
        total=total,
    )


@router.get("/invites", response_model=OrgInviteListResponse)
async def list_invites(
    status: str | None = Query(default="pending"),
    department_id: int | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
    ctx: TenantContext = Depends(
        require_permission("APPROVE_STUDENT", "UPLOAD_STUDENTS", "VIEW_ALL_STUDENTS", "VIEW_DEPARTMENT_STUDENTS")
    ),
) -> OrgInviteListResponse:
    items, total = await svc.list_invites(
        db, ctx, status=status, department_id=department_id
    )
    return OrgInviteListResponse(
        items=[OrgInviteResponse.model_validate(i) for i in items],
        total=total,
    )


@router.post("/invite", response_model=StudentInviteResult, status_code=201)
async def invite_students(
    body: StudentInviteRequest,
    db: AsyncSession = Depends(get_db),
    ctx: TenantContext = Depends(require_permission("UPLOAD_STUDENTS", "APPROVE_STUDENT")),
) -> StudentInviteResult:
    try:
        result = await svc.invite_emails(
            db,
            ctx,
            emails=[str(e) for e in body.emails],
            department_id=body.department_id,
            source=body.source,
            auto_enroll=body.auto_enroll,
            skip_approval=body.skip_approval,
        )
    except svc.StudentPortalError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc

    out_items: list = []
    for i in result["items"]:
        if "auth_status" in i:
            out_items.append(OrgStudentResponse.model_validate(i))
        else:
            out_items.append(OrgInviteResponse.model_validate(i))

    emailed = bool(result.get("emailed"))
    return StudentInviteResult(
        created=result["created"],
        skipped=result["skipped"],
        errors=result["errors"],
        items=out_items,
        emailed=emailed,
        email_sent=emailed,
        message=result.get("message") or "",
        setup_url=result.get("setup_url"),
        activation_token=result.get("activation_token"),
    )


@router.post("", response_model=StudentManualCreateResponse, status_code=201)
async def create_student_manual(
    body: StudentManualCreate,
    db: AsyncSession = Depends(get_db),
    ctx: TenantContext = Depends(require_permission("UPLOAD_STUDENTS", "APPROVE_STUDENT")),
) -> StudentManualCreateResponse:
    try:
        payload = await svc.create_manual(
            db,
            ctx,
            name=body.name,
            email=str(body.email),
            department_id=body.department_id,
            roll_number=body.roll_number,
            batch_year=body.batch_year,
            source=body.source,
            auto_enroll=body.auto_enroll,
            skip_approval=body.skip_approval,
        )
    except svc.StudentPortalError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc

    student = (
        OrgStudentResponse.model_validate(payload["student"])
        if payload.get("student")
        else None
    )
    invitation = (
        OrgInviteResponse.model_validate(payload["invitation"])
        if payload.get("invitation")
        else None
    )
    return StudentManualCreateResponse(
        student=student,
        invitation=invitation,
        email_sent=bool(payload.get("email_sent")),
        emailed=bool(payload.get("emailed")),
        activation_token=payload.get("activation_token"),
        setup_url=payload.get("setup_url"),
        message=payload.get("message") or "",
    )


@router.post("/import", response_model=StudentImportResult, status_code=201)
async def import_students(
    body: StudentImportRequest,
    db: AsyncSession = Depends(get_db),
    ctx: TenantContext = Depends(require_permission("UPLOAD_STUDENTS")),
) -> StudentImportResult:
    rows = [
        {
            "email": str(r.email),
            "name": r.name,
            "roll_number": r.roll_number,
            "batch_year": r.batch_year,
        }
        for r in body.rows
    ]
    try:
        result = await svc.import_students(
            db,
            ctx,
            department_id=body.department_id,
            rows=rows,
            csv_text=body.csv_text,
            send_invite_email=body.send_invite_email,
            source=body.source,
            auto_enroll=body.auto_enroll,
            skip_approval=body.skip_approval,
        )
    except svc.StudentPortalError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc

    out_items: list = []
    for i in result["items"]:
        if "auth_status" in i:
            out_items.append(OrgStudentResponse.model_validate(i))
        else:
            out_items.append(OrgInviteResponse.model_validate(i))

    return StudentImportResult(
        created=result["created"],
        updated=result["updated"],
        skipped=result["skipped"],
        errors=result["errors"],
        items=out_items,
        message=result.get("message") or "",
    )


@router.post("/invites/{invite_id}/approve", response_model=StudentApproveResponse)
async def approve_invite(
    invite_id: int,
    body: StudentDecisionRequest | None = None,
    db: AsyncSession = Depends(get_db),
    ctx: TenantContext = Depends(require_permission("APPROVE_STUDENT")),
) -> StudentApproveResponse:
    decision = body or StudentDecisionRequest()
    try:
        payload = await svc.approve_invite(
            db, ctx, invite_id=invite_id, send_email=decision.send_email
        )
    except svc.StudentPortalError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc
    return StudentApproveResponse(
        student=OrgStudentResponse.model_validate(payload["student"]),
        email_sent=payload["email_sent"],
        emailed=payload["email_sent"],
        activation_token=payload.get("activation_token"),
        setup_url=payload.get("setup_url"),
        message=payload.get("message") or "",
    )


@router.post("/invites/{invite_id}/reject", response_model=StudentRejectResponse)
async def reject_invite(
    invite_id: int,
    body: StudentDecisionRequest | None = None,
    db: AsyncSession = Depends(get_db),
    ctx: TenantContext = Depends(require_permission("APPROVE_STUDENT")),
) -> StudentRejectResponse:
    decision = body or StudentDecisionRequest()
    try:
        payload = await svc.reject_invite(
            db, ctx, invite_id=invite_id, send_email=decision.send_email
        )
    except svc.StudentPortalError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc
    return StudentRejectResponse(
        emailed=bool(payload.get("emailed")),
        email_sent=bool(payload.get("email_sent")),
        message=payload.get("message") or "",
        invitation=OrgInviteResponse.model_validate(payload["invitation"])
        if payload.get("invitation")
        else None,
    )


def _approve_like_response(payload: dict) -> StudentApproveResponse:
    return StudentApproveResponse(
        student=OrgStudentResponse.model_validate(payload["student"]),
        email_sent=bool(payload.get("email_sent")),
        emailed=bool(payload.get("emailed", payload.get("email_sent"))),
        activation_token=payload.get("activation_token"),
        setup_url=payload.get("setup_url"),
        message=payload.get("message") or "",
    )


@router.post("/{student_id}/resend-invite", response_model=StudentApproveResponse)
@router.post("/{student_id}/resend-setup", response_model=StudentApproveResponse)
@router.post("/{student_id}/resend-activation", response_model=StudentApproveResponse)
async def resend_student_setup_link(
    student_id: int,
    db: AsyncSession = Depends(get_db),
    ctx: TenantContext = Depends(require_permission("APPROVE_STUDENT", "UPLOAD_STUDENTS")),
) -> StudentApproveResponse:
    """Regenerate set-password email/link for a student (FE resend button)."""
    try:
        payload = await svc.resend_setup_link(db, ctx, student_id=student_id)
    except svc.StudentPortalError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc
    return _approve_like_response(payload)


@router.patch("/{student_id}", response_model=StudentUpdateResponse)
async def patch_student(
    student_id: int,
    body: StudentPatchRequest,
    db: AsyncSession = Depends(get_db),
    ctx: TenantContext = Depends(
        require_permission("MANAGE_USER_STATUS", "UPLOAD_STUDENTS", "APPROVE_STUDENT")
    ),
) -> StudentUpdateResponse:
    try:
        row = await svc.patch_student(
            db,
            ctx,
            student_id=student_id,
            fields=body.model_dump(exclude_unset=True),
        )
    except svc.StudentPortalError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc
    return StudentUpdateResponse(
        student=OrgStudentResponse.model_validate(row),
        message="Student updated.",
    )


@router.delete("/{student_id}", response_model=StudentDeleteResponse)
async def delete_student(
    student_id: int,
    db: AsyncSession = Depends(get_db),
    ctx: TenantContext = Depends(
        require_permission("MANAGE_USER_STATUS", "UPLOAD_STUDENTS", "APPROVE_STUDENT")
    ),
) -> StudentDeleteResponse:
    try:
        await svc.delete_student(db, ctx, student_id=student_id)
    except svc.StudentPortalError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc
    return StudentDeleteResponse(ok=True, message="Student removed.")

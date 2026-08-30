"""
Org Portal departments — FE contract under /organizations/departments.

Aliases existing /departments CRUD + first-class HOD lifecycle.
"""

from __future__ import annotations

from typing import Optional, Union

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.audit import write_audit
from app.common.authz import require_permission
from app.common.deps import get_db, require_api_key
from app.common.security.auth_errors import (
    TOKEN_INVALID,
    TOKEN_MISSING,
    auth_detail,
    raise_unauthorized,
)
from app.common.security.jwt import decode_access_token
from app.common.tenant.context import TenantContext
from app.common.tenant.deps import build_tenant_context
from app.departments import hod as hod_service
from app.departments import service as dept_service
from app.departments.schemas import (
    DepartmentCreate,
    DepartmentUpdate,
    HodInviteRequest,
    HodLifecycleResponse,
    HodReplaceRequest,
    HodRevokeRequest,
    OrgDepartmentResponse,
)
from app.organizations import service as org_service
from app.organizations.schemas import PublicDepartmentItem, PublicDepartmentsResponse
from app.users import service as user_service

router = APIRouter(
    prefix="/organizations/departments",
    tags=["Organization Departments"],
    dependencies=[Depends(require_api_key)],
)

_bearer = HTTPBearer(auto_error=False)


def _dept_response(payload: dict) -> OrgDepartmentResponse:
    return OrgDepartmentResponse.model_validate(payload)


def _lifecycle_response(payload: dict) -> HodLifecycleResponse:
    return HodLifecycleResponse.model_validate(payload)


def _dept_http(exc: dept_service.DepartmentError) -> HTTPException:
    return HTTPException(
        status_code=exc.status_code,
        detail=auth_detail(
            code=exc.code or "DEPARTMENT_ERROR",
            message=exc.message,
        ),
    )


@router.get("", response_model=Union[list[OrgDepartmentResponse], PublicDepartmentsResponse])
async def list_org_departments(
    organization_code: Optional[str] = Query(
        default=None,
        description="Public enroll: list active departments for this college code (no JWT).",
    ),
    include: str = Query(
        default="full",
        description=(
            "Authenticated list detail: "
            "'full' = mentors + student counts + history (batch); "
            "'light' / 'minimal' / 'options' = id/name/code only (for dropdowns)."
        ),
    ),
    db: AsyncSession = Depends(get_db),
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(_bearer),
) -> Union[list[OrgDepartmentResponse], PublicDepartmentsResponse]:
    # Public student-enroll path (FE fallback)
    if organization_code:
        try:
            depts = await org_service.list_active_departments_for_college_code(
                db, organization_code
            )
        except org_service.OrgError as exc:
            raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc
        return PublicDepartmentsResponse(
            departments=[PublicDepartmentItem.model_validate(d) for d in depts]
        )

    # Authenticated TPO/HOD list
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise_unauthorized(code=TOKEN_MISSING, message="Missing Authorization Bearer token.")
    payload = decode_access_token(credentials.credentials, expected_scope="tenant")
    try:
        user_id = int(payload["sub"])
    except (KeyError, TypeError, ValueError):
        raise_unauthorized(code=TOKEN_INVALID, message="Invalid token subject.")
    try:
        user = await user_service.get_user(db, user_id)
    except user_service.UserServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc
    ctx = await build_tenant_context(db, user)

    items = await dept_service.list_departments(db, organization_id=ctx.organization_id)
    mode = (include or "full").strip().lower()
    if mode in {"light", "minimal", "options"}:
        return [_dept_response(hod_service.light_department_payload(d)) for d in items]

    enriched = await hod_service.enrich_departments_batch(
        db, items, include_history=True
    )
    return [_dept_response(row) for row in enriched]


@router.post("", response_model=OrgDepartmentResponse, status_code=201)
async def create_org_department(
    body: DepartmentCreate,
    db: AsyncSession = Depends(get_db),
    ctx: TenantContext = Depends(require_permission("CREATE_DEPARTMENT")),
) -> OrgDepartmentResponse:
    if body.organization_id is not None and body.organization_id != ctx.organization_id:
        raise HTTPException(status_code=403, detail="Cannot create department in another org.")
    try:
        dept = await dept_service.create_department(
            db,
            organization_id=ctx.organization_id,
            name=body.name,
            code=body.code,
        )
        await write_audit(
            db,
            organization_id=ctx.organization_id,
            actor_user_id=ctx.user_id,
            action="department.create",
            entity_type="department",
            entity_id=dept.id,
            payload={"code": dept.code, "name": dept.name},
        )
    except dept_service.DepartmentError as exc:
        raise _dept_http(exc) from exc
    return _dept_response(await hod_service.enrich_department(db, dept))


@router.put("/{department_id}", response_model=OrgDepartmentResponse)
async def update_org_department(
    department_id: int,
    body: DepartmentUpdate,
    db: AsyncSession = Depends(get_db),
    ctx: TenantContext = Depends(require_permission("CREATE_DEPARTMENT")),
) -> OrgDepartmentResponse:
    try:
        dept = await dept_service.get_department(db, department_id)
        if dept.organization_id != ctx.organization_id:
            raise HTTPException(status_code=403, detail="Department not in your organization.")
        dept = await dept_service.update_department(
            db,
            department_id,
            **body.model_dump(exclude_unset=True, exclude={"hod_name", "hod_email"}),
        )
        await write_audit(
            db,
            organization_id=ctx.organization_id,
            actor_user_id=ctx.user_id,
            action="department.update",
            entity_type="department",
            entity_id=dept.id,
            payload=body.model_dump(exclude_unset=True, exclude={"hod_name", "hod_email"}),
        )
    except dept_service.DepartmentError as exc:
        raise _dept_http(exc) from exc
    return _dept_response(await hod_service.enrich_department(db, dept))


@router.delete("/{department_id}", response_model=OrgDepartmentResponse)
async def delete_org_department(
    department_id: int,
    db: AsyncSession = Depends(get_db),
    ctx: TenantContext = Depends(require_permission("CREATE_DEPARTMENT")),
) -> OrgDepartmentResponse:
    try:
        dept = await dept_service.get_department(db, department_id)
        if dept.organization_id != ctx.organization_id:
            raise HTTPException(status_code=403, detail="Department not in your organization.")
        dept = await dept_service.soft_delete_department(db, department_id)
        await write_audit(
            db,
            organization_id=ctx.organization_id,
            actor_user_id=ctx.user_id,
            action="department.delete",
            entity_type="department",
            entity_id=dept.id,
        )
    except dept_service.DepartmentError as exc:
        raise _dept_http(exc) from exc
    return _dept_response(await hod_service.enrich_department(db, dept))


@router.post(
    "/{department_id}/hod",
    response_model=HodLifecycleResponse,
    status_code=201,
)
async def invite_department_hod(
    department_id: int,
    body: HodInviteRequest,
    db: AsyncSession = Depends(get_db),
    ctx: TenantContext = Depends(require_permission("CREATE_HOD")),
) -> HodLifecycleResponse:
    try:
        payload, _ = await hod_service.invite_hod(
            db,
            department_id=department_id,
            name=body.name,
            email=str(body.email),
            actor=ctx.user,
        )
    except dept_service.DepartmentError as exc:
        raise _dept_http(exc) from exc
    except Exception as exc:
        from app.users.service import UserServiceError

        if isinstance(exc, UserServiceError):
            raise HTTPException(
                status_code=exc.status_code,
                detail=auth_detail(code="HOD_EMAIL_CONFLICT", message=exc.message),
            ) from exc
        raise
    return _lifecycle_response(payload)


@router.post("/{department_id}/hod/reinvite", response_model=HodLifecycleResponse)
async def reinvite_department_hod(
    department_id: int,
    db: AsyncSession = Depends(get_db),
    ctx: TenantContext = Depends(require_permission("CREATE_HOD")),
) -> HodLifecycleResponse:
    try:
        payload = await hod_service.reinvite_hod(
            db, department_id=department_id, actor=ctx.user
        )
    except dept_service.DepartmentError as exc:
        raise _dept_http(exc) from exc
    return _lifecycle_response(payload)


@router.post("/{department_id}/hod/revoke", response_model=HodLifecycleResponse)
async def revoke_department_hod(
    department_id: int,
    body: HodRevokeRequest | None = None,
    db: AsyncSession = Depends(get_db),
    ctx: TenantContext = Depends(require_permission("CREATE_HOD")),
) -> HodLifecycleResponse:
    try:
        payload = await hod_service.revoke_hod(
            db,
            department_id=department_id,
            actor=ctx.user,
            reason=(body.reason if body else None),
        )
    except dept_service.DepartmentError as exc:
        raise _dept_http(exc) from exc
    return _lifecycle_response(payload)


@router.post("/{department_id}/hod/replace", response_model=HodLifecycleResponse)
async def replace_department_hod(
    department_id: int,
    body: HodReplaceRequest,
    db: AsyncSession = Depends(get_db),
    ctx: TenantContext = Depends(require_permission("CREATE_HOD")),
) -> HodLifecycleResponse:
    try:
        payload = await hod_service.replace_hod(
            db,
            department_id=department_id,
            name=body.name,
            email=str(body.email),
            actor=ctx.user,
            reason=body.reason,
        )
    except dept_service.DepartmentError as exc:
        raise _dept_http(exc) from exc
    except Exception as exc:
        from app.users.service import UserServiceError

        if isinstance(exc, UserServiceError):
            raise HTTPException(
                status_code=exc.status_code,
                detail=auth_detail(code="HOD_EMAIL_CONFLICT", message=exc.message),
            ) from exc
        raise
    return _lifecycle_response(payload)


@router.post(
    "/{department_id}/coordinator",
    response_model=HodLifecycleResponse,
    status_code=201,
)
async def invite_department_coordinator(
    department_id: int,
    body: HodInviteRequest,
    db: AsyncSession = Depends(get_db),
    ctx: TenantContext = Depends(require_permission("CREATE_HOD")),
) -> HodLifecycleResponse:
    try:
        payload, _ = await hod_service.invite_coordinator(
            db,
            department_id=department_id,
            name=body.name,
            email=str(body.email),
            actor=ctx.user,
        )
    except dept_service.DepartmentError as exc:
        raise _dept_http(exc) from exc
    except Exception as exc:
        from app.users.service import UserServiceError

        if isinstance(exc, UserServiceError):
            raise HTTPException(
                status_code=exc.status_code,
                detail=auth_detail(code="HOD_EMAIL_CONFLICT", message=exc.message),
            ) from exc
        raise
    return _lifecycle_response(payload)


@router.post("/{department_id}/coordinator/reinvite", response_model=HodLifecycleResponse)
async def reinvite_department_coordinator(
    department_id: int,
    db: AsyncSession = Depends(get_db),
    ctx: TenantContext = Depends(require_permission("CREATE_HOD")),
) -> HodLifecycleResponse:
    try:
        payload = await hod_service.reinvite_coordinator(
            db, department_id=department_id, actor=ctx.user
        )
    except dept_service.DepartmentError as exc:
        raise _dept_http(exc) from exc
    return _lifecycle_response(payload)


@router.post("/{department_id}/coordinator/revoke", response_model=HodLifecycleResponse)
async def revoke_department_coordinator(
    department_id: int,
    body: HodRevokeRequest | None = None,
    db: AsyncSession = Depends(get_db),
    ctx: TenantContext = Depends(require_permission("CREATE_HOD")),
) -> HodLifecycleResponse:
    try:
        payload = await hod_service.revoke_coordinator(
            db,
            department_id=department_id,
            actor=ctx.user,
            reason=(body.reason if body else None),
        )
    except dept_service.DepartmentError as exc:
        raise _dept_http(exc) from exc
    return _lifecycle_response(payload)


@router.post("/{department_id}/coordinator/replace", response_model=HodLifecycleResponse)
async def replace_department_coordinator(
    department_id: int,
    body: HodReplaceRequest,
    db: AsyncSession = Depends(get_db),
    ctx: TenantContext = Depends(require_permission("CREATE_HOD")),
) -> HodLifecycleResponse:
    try:
        payload = await hod_service.replace_coordinator(
            db,
            department_id=department_id,
            name=body.name,
            email=str(body.email),
            actor=ctx.user,
            reason=body.reason,
        )
    except dept_service.DepartmentError as exc:
        raise _dept_http(exc) from exc
    except Exception as exc:
        from app.users.service import UserServiceError

        if isinstance(exc, UserServiceError):
            raise HTTPException(
                status_code=exc.status_code,
                detail=auth_detail(code="HOD_EMAIL_CONFLICT", message=exc.message),
            ) from exc
        raise
    return _lifecycle_response(payload)

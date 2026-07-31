"""
User routes (Track A — TPO/HOD identity).

POST   /users
GET    /users
GET    /users/{id}
PUT    /users/{id}
DELETE /users/{id}
PUT    /users/{id}/approve
PUT    /users/{id}/reject
POST   /users/import
"""

from __future__ import annotations

from typing import Union

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.authz import require_permission
from app.common.deps import get_db, require_api_key
from app.common.security.jwt import decode_access_token
from app.common.tenant.context import TenantContext
from app.common.tenant.deps import build_tenant_context, get_tenant_context
from app.models.enums import RoleCode
from app.models.user import User
from app.users import service as user_service
from app.users.schemas import (
    UserCreate,
    UserImportResult,
    UserInviteResponse,
    UserListResponse,
    UserResponse,
    UserUpdate,
)

router = APIRouter(
    prefix="/users",
    tags=["Users"],
    dependencies=[Depends(require_api_key)],
)

_bearer = HTTPBearer(auto_error=False)


def _to_response(user: User) -> UserResponse:
    return UserResponse(
        id=user.id,
        organization_id=user.organization_id,
        department_id=user.department_id,
        role_id=user.role_id,
        role_code=user.role.role_code if user.role else None,
        first_name=user.first_name,
        last_name=user.last_name,
        email=user.email,
        mobile=user.mobile,
        username=user.username,
        status=user.status,
        roll_number=user.roll_number,
        batch_year=user.batch_year,
        approved_by=user.approved_by,
        approved_at=user.approved_at,
        created_at=user.created_at,
        updated_at=user.updated_at,
    )


async def _optional_user(
    credentials: HTTPAuthorizationCredentials | None,
    db: AsyncSession,
) -> User | None:
    if credentials is None or credentials.scheme.lower() != "bearer":
        return None
    payload = decode_access_token(credentials.credentials, expected_scope="tenant")
    try:
        user_id = int(payload["sub"])
    except (KeyError, TypeError, ValueError):
        return None
    try:
        return await user_service.get_user(db, user_id)
    except user_service.UserServiceError:
        return None


@router.post("/import", response_model=UserImportResult)
async def import_users(
    file: UploadFile = File(..., description="CSV: first_name,last_name,email,username,password,department_id[,mobile]"),
    db: AsyncSession = Depends(get_db),
    ctx: TenantContext = Depends(require_permission("UPLOAD_STUDENTS")),
) -> UserImportResult:
    raw = await file.read()
    try:
        text = raw.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise HTTPException(status_code=422, detail="CSV must be UTF-8.") from exc
    try:
        created, skipped, _err_count, errors = await user_service.import_students_csv(
            db, actor=ctx.user, csv_text=text
        )
    except user_service.UserServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc
    return UserImportResult(
        created=len(created),
        skipped=skipped,
        errors=errors,
        items=[_to_response(u) for u in created],
    )


@router.post("", response_model=Union[UserInviteResponse, UserResponse], status_code=201)
async def create_user(
    body: UserCreate,
    db: AsyncSession = Depends(get_db),
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
) -> Union[UserInviteResponse, UserResponse]:
    actor = await _optional_user(credentials, db)

    if body.role_code == RoleCode.ORG_ADMIN.value and actor is not None:
        raise HTTPException(
            status_code=403,
            detail="ORG_ADMIN must be created by platform (API key only).",
        )

    if body.role_code == RoleCode.DEPARTMENT_ADMIN.value:
        if actor is None:
            raise HTTPException(status_code=401, detail="Login as TPO required to create HOD.")
        ctx = await build_tenant_context(db, actor)
        if not ctx.has_permission("CREATE_HOD"):
            raise HTTPException(status_code=403, detail="Missing permission: CREATE_HOD")
        body = body.model_copy(update={"organization_id": ctx.organization_id})

    try:
        user, raw_token, expires = await user_service.create_user(
            db,
            first_name=body.first_name,
            last_name=body.last_name,
            email=str(body.email),
            username=body.username,
            password=body.password,
            role_code=body.role_code,
            organization_id=body.organization_id,
            organization_code=body.organization_code,
            department_id=body.department_id,
            mobile=body.mobile,
            individual=body.individual,
            created_by=actor,
            activation_hours=body.activation_hours,
        )
    except user_service.UserServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc

    if raw_token and expires:
        email_sent = await user_service.send_hod_invite_email(
            user=user, raw_token=raw_token, expires=expires
        )
        return UserInviteResponse(
            user=_to_response(user),
            email_sent=email_sent,
            activation_token=None if email_sent else raw_token,
            activation_url=None if email_sent else user_service.activation_link(raw_token),
            message=(
                "HOD invited and activation email sent."
                if email_sent
                else "HOD invited. Email not sent; share activation_token manually."
            ),
        )
    return _to_response(user)


@router.get("", response_model=UserListResponse)
async def list_users(
    department_id: int | None = Query(default=None),
    status: str | None = Query(default=None),
    role_code: str | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
    ctx: TenantContext = Depends(
        require_permission(
            "VIEW_ALL_STUDENTS",
            "VIEW_DEPARTMENT_STUDENTS",
            "CREATE_HOD",
        )
    ),
) -> UserListResponse:
    dept_filter = department_id
    if not ctx.sees_all_students:
        dept_filter = ctx.department_id

    items, total = await user_service.list_users(
        db,
        organization_id=ctx.organization_id,
        department_id=dept_filter,
        status=status,
        role_code=role_code,
    )
    return UserListResponse(items=[_to_response(u) for u in items], total=total)


@router.get("/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    ctx: TenantContext = Depends(get_tenant_context),
) -> UserResponse:
    try:
        user = await user_service.get_user(db, user_id)
    except user_service.UserServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc
    if user.organization_id != ctx.organization_id:
        raise HTTPException(status_code=403, detail="Cannot access user in another org.")
    if ctx.role == RoleCode.STUDENT.value and ctx.user_id != user_id:
        raise HTTPException(status_code=403, detail="Students can only view themselves.")
    if (
        not ctx.sees_all_students
        and ctx.role == RoleCode.DEPARTMENT_ADMIN.value
        and user.department_id != ctx.department_id
        and ctx.user_id != user_id
    ):
        raise HTTPException(status_code=403, detail="Outside your department.")
    return _to_response(user)


@router.put("/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: int,
    body: UserUpdate,
    db: AsyncSession = Depends(get_db),
    ctx: TenantContext = Depends(get_tenant_context),
) -> UserResponse:
    try:
        target = await user_service.get_user(db, user_id)
        if target.organization_id != ctx.organization_id:
            raise HTTPException(status_code=403, detail="Cannot update user in another org.")
        if ctx.role == RoleCode.STUDENT.value and ctx.user_id != user_id:
            raise HTTPException(status_code=403, detail="Students can only update themselves.")
        if ctx.role == RoleCode.STUDENT.value and body.status is not None:
            raise HTTPException(status_code=403, detail="Students cannot change status.")
        if body.status is not None and not ctx.has_permission("MANAGE_USER_STATUS"):
            if ctx.user_id != user_id:
                raise HTTPException(
                    status_code=403, detail="Missing permission: MANAGE_USER_STATUS"
                )

        user = await user_service.update_user(
            db,
            user_id,
            **body.model_dump(exclude_unset=True),
        )
    except user_service.UserServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc
    return _to_response(user)


@router.delete("/{user_id}", response_model=UserResponse)
async def delete_user(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    ctx: TenantContext = Depends(require_permission("MANAGE_USER_STATUS", "CREATE_HOD")),
) -> UserResponse:
    try:
        user = await user_service.soft_delete_user(db, user_id=user_id, actor=ctx.user)
    except user_service.UserServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc
    return _to_response(user)


@router.put("/{user_id}/approve", response_model=UserResponse)
async def approve_user(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    ctx: TenantContext = Depends(require_permission("APPROVE_STUDENT")),
) -> UserResponse:
    try:
        user, _token, _url, _sent = await user_service.approve_user(
            db, user_id=user_id, approver=ctx.user
        )
    except user_service.UserServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc
    return _to_response(user)


@router.put("/{user_id}/reject", response_model=UserResponse)
async def reject_user(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    ctx: TenantContext = Depends(require_permission("APPROVE_STUDENT")),
) -> UserResponse:
    try:
        user = await user_service.reject_user(db, user_id=user_id, approver=ctx.user)
    except user_service.UserServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc
    return _to_response(user)

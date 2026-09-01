"""
Auth routes.

POST /auth/login
POST /auth/logout
GET  /auth/me
POST /auth/change-password
POST /auth/forgot-password
POST /auth/reset-password
POST /auth/activate
POST /auth/activate-hod
POST /auth/activate-student
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import service as auth_service
from app.auth.schemas import (
    ActivateAccountRequest,
    ActivateAccountResponse,
    ChangePasswordRequest,
    ForgotPasswordRequest,
    ForgotPasswordResponse,
    LoginRequest,
    MeResponse,
    MessageResponse,
    ResetPasswordRequest,
    TokenResponse,
)
from app.common.deps import get_current_active_user, get_db, require_api_key
from app.common.rate_limit import limiter
from app.common.security.auth_errors import auth_detail
from app.common.security.jwt import create_access_token
from app.common.tenant.deps import build_tenant_context
from app.models.enums import RoleCode
from app.organizations.hod_access_schemas import HodAccessPolicy
from app.organizations.hod_access_service import get_hod_access_policy
from app.models.user import User

router = APIRouter(
    prefix="/auth",
    tags=["Auth"],
    dependencies=[Depends(require_api_key)],
)


def _auth_http(exc: auth_service.AuthError) -> HTTPException:
    code = exc.code or (
        "INVALID_CREDENTIALS"
        if exc.status_code == 401
        else "ORG_SUSPENDED"
        if exc.status_code == 403
        else "AUTH_ERROR"
    )
    detail = auth_detail(code=code, message=exc.message)
    if getattr(exc, "extra", None):
        detail.update({k: v for k, v in exc.extra.items() if v is not None})
    return HTTPException(
        status_code=exc.status_code,
        detail=detail,
    )


async def _to_me(db: AsyncSession, user: User) -> MeResponse:
    ctx = await build_tenant_context(db, user)
    role_code = ctx.role
    dept = user.department
    org_type = (
        user.organization.organization_type if user.organization else "COLLEGE"
    )
    is_individual = str(org_type).upper() == "PUBLIC"
    hod_access = None
    if role_code in (RoleCode.ORG_ADMIN.value, RoleCode.DEPARTMENT_ADMIN.value):
        if user.organization_id is not None:
            policy = await get_hod_access_policy(db, user.organization_id)
            hod_access = HodAccessPolicy(**policy)
    return MeResponse(
        id=user.id,
        user_id=user.id,
        name=auth_service.user_display_name(user),
        email=user.email,
        role=auth_service.fe_role_alias(role_code),
        role_code=role_code,
        role_name=user.role.role_name if user.role else "",
        dept_admin_title=auth_service.dept_admin_title_for(user),
        role_label=auth_service.role_display_label(user, role_code),
        organization_id=user.organization_id,
        organization_code=user.organization.code if user.organization else "",
        organization_name=user.organization.name if user.organization else "",
        organization_type=org_type,
        is_individual=is_individual,
        department_id=user.department_id,
        department_name=dept.name if dept else "",
        department_code=dept.code if dept else "",
        permissions=sorted(ctx.permissions),
        hod_access=hod_access,
        must_change_password=bool(getattr(user, "must_change_password", False)),
        first_name=user.first_name,
        last_name=user.last_name,
        mobile=user.mobile,
        username=user.username,
        status=user.status,
        college_name=getattr(user, "college_name", None),
        course_or_branch=getattr(user, "course_or_branch", None),
        batch_year=getattr(user, "batch_year", None),
        roll_number=getattr(user, "roll_number", None),
        created_at=user.created_at,
    )


@router.post("/login", response_model=TokenResponse)
@limiter.limit("500/minute")
async def login(
    request: Request, body: LoginRequest, db: AsyncSession = Depends(get_db)
) -> TokenResponse:
    try:
        user = await auth_service.authenticate_user(
            db,
            email=str(body.email).lower() if body.email else None,
            username=body.username,
            password=body.password,
            organization_code=body.organization_code,
        )
    except auth_service.AuthError as exc:
        raise _auth_http(exc) from exc

    try:
        auth_service.ensure_login_portal_allowed(
            user,
            portal=body.portal,
            organization_code=body.organization_code,
        )
    except auth_service.AuthError as exc:
        raise _auth_http(exc) from exc

    permissions = await auth_service.permissions_for_user(db, user)
    role_code = user.role.role_code if user.role else ""
    fe_role = auth_service.fe_role_alias(role_code)
    token = create_access_token(
        user_id=user.id,
        scope="tenant",
        extra={
            "role": role_code,
            "fe_role": fe_role,
            "org_id": user.organization_id,
            "department_id": user.department_id,
            "permissions": permissions,
        },
    )
    me = await _to_me(db, user)
    return TokenResponse(
        access_token=token,
        expires_in_minutes=auth_service.token_expires_minutes(),
        user=me,
        user_id=user.id,
        organization_id=user.organization_id,
        department_id=user.department_id,
        role=fe_role,
        permissions=permissions,
    )


@router.post("/logout", response_model=MessageResponse)
async def logout(
    _user: User = Depends(get_current_active_user),
) -> MessageResponse:
    return MessageResponse(message="Logged out. Discard the access token on the client.")


@router.get("/me", response_model=MeResponse)
async def me(
    user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> MeResponse:
    return await _to_me(db, user)


@router.post("/change-password", response_model=MessageResponse)
async def change_password(
    body: ChangePasswordRequest,
    user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> MessageResponse:
    try:
        await auth_service.change_password(
            db,
            user=user,
            current_password=body.current_password,
            new_password=body.new_password,
        )
    except auth_service.AuthError as exc:
        raise _auth_http(exc) from exc
    return MessageResponse(message="Password updated.")


@router.post("/forgot-password", response_model=ForgotPasswordResponse)
@limiter.limit("20/minute")
async def forgot_password(
    request: Request,
    body: ForgotPasswordRequest,
    db: AsyncSession = Depends(get_db),
) -> ForgotPasswordResponse:
    message, emailed, _reset_url = await auth_service.request_password_reset(
        db,
        email=str(body.email) if body.email else None,
        username=body.username,
        identifier=body.identifier,
        organization_code=body.organization_code,
        portal=body.portal,
    )
    # Never reveal whether the account exists or mail was delivered.
    _ = emailed
    return ForgotPasswordResponse(
        message=message,
        emailed=False,
        # Never return reset_url on this public endpoint (account-takeover vector).
        reset_url=None,
    )


@router.post("/reset-password", response_model=MessageResponse)
@limiter.limit("100/minute")
async def reset_password(
    request: Request,
    body: ResetPasswordRequest,
    db: AsyncSession = Depends(get_db),
) -> MessageResponse:
    try:
        await auth_service.reset_password(
            db, token=body.token, new_password=body.new_password
        )
    except auth_service.AuthError as exc:
        raise _auth_http(exc) from exc
    return MessageResponse(message="Password has been reset. You can log in now.")


@router.post("/activate", response_model=ActivateAccountResponse)
@limiter.limit("100/minute")
async def activate_account(
    request: Request,
    body: ActivateAccountRequest,
    db: AsyncSession = Depends(get_db),
) -> ActivateAccountResponse:
    """Activate INVITED TPO or HOD (set password). Then use POST /auth/login."""
    try:
        user = await auth_service.activate_invited_user(
            db, token=body.token, new_password=body.new_password
        )
    except auth_service.AuthError as exc:
        raise _auth_http(exc) from exc
    org_code = user.organization.code if user.organization else None
    return ActivateAccountResponse(
        message="Account activated. You can log in now.",
        organization_code=org_code,
    )


@router.post("/activate-hod", response_model=ActivateAccountResponse)
@limiter.limit("100/minute")
async def activate_hod(
    request: Request,
    body: ActivateAccountRequest,
    db: AsyncSession = Depends(get_db),
) -> ActivateAccountResponse:
    """FE contract: POST /auth/activate-hod — API key only, no JWT."""
    try:
        user = await auth_service.activate_invited_user(
            db, token=body.token, new_password=body.new_password
        )
        await auth_service.audit_hod_activate(db, user)
    except auth_service.AuthError as exc:
        raise _auth_http(exc) from exc
    org_code = user.organization.code if user.organization else None
    return ActivateAccountResponse(
        message="Password set. You can log in to the Organization Portal.",
        organization_code=org_code,
    )


@router.post("/activate-student", response_model=ActivateAccountResponse)
@limiter.limit("100/minute")
async def activate_student(
    request: Request,
    body: ActivateAccountRequest,
    db: AsyncSession = Depends(get_db),
) -> ActivateAccountResponse:
    """FE: /studentportal/set-password → POST /auth/activate-student."""
    try:
        user = await auth_service.activate_invited_user(
            db, token=body.token, new_password=body.new_password
        )
    except auth_service.AuthError as exc:
        raise _auth_http(exc) from exc
    org_code = user.organization.code if user.organization else None
    return ActivateAccountResponse(
        message="Password set. You can log in to the Student Portal.",
        organization_code=org_code,
    )

"""
Auth routes.

POST /auth/login
POST /auth/logout
GET  /auth/me
POST /auth/change-password
POST /auth/forgot-password
POST /auth/reset-password
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import service as auth_service
from app.auth.schemas import (
    ActivateAccountRequest,
    ChangePasswordRequest,
    ForgotPasswordRequest,
    LoginRequest,
    MeResponse,
    MessageResponse,
    ResetPasswordRequest,
    TokenResponse,
)
from app.common.deps import get_current_active_user, get_db, require_api_key
from app.common.security.jwt import create_access_token
from app.common.tenant.deps import build_tenant_context
from app.models.user import User

router = APIRouter(
    prefix="/auth",
    tags=["Auth"],
    dependencies=[Depends(require_api_key)],
)


async def _to_me(db: AsyncSession, user: User) -> MeResponse:
    ctx = await build_tenant_context(db, user)
    return MeResponse(
        id=user.id,
        user_id=user.id,
        organization_id=user.organization_id,
        organization_code=user.organization.code,
        organization_name=user.organization.name,
        organization_type=user.organization.organization_type,
        department_id=user.department_id,
        department_code=user.department.code if user.department else None,
        role=ctx.role,
        role_code=ctx.role,
        role_name=user.role.role_name,
        permissions=sorted(ctx.permissions),
        first_name=user.first_name,
        last_name=user.last_name,
        email=user.email,
        mobile=user.mobile,
        username=user.username,
        status=user.status,
        created_at=user.created_at,
    )


@router.post("/login", response_model=TokenResponse)
async def login(body: LoginRequest, db: AsyncSession = Depends(get_db)) -> TokenResponse:
    try:
        user = await auth_service.authenticate_user(
            db,
            email=str(body.email).lower() if body.email else None,
            username=body.username,
            password=body.password,
            organization_code=body.organization_code,
        )
    except auth_service.AuthError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc

    permissions = await auth_service.permissions_for_user(db, user)
    token = create_access_token(
        user_id=user.id,
        scope="tenant",
        extra={
            "role": user.role.role_code,
            "org_id": user.organization_id,
            "department_id": user.department_id,
            "permissions": permissions,
        },
    )
    return TokenResponse(
        access_token=token,
        expires_in_minutes=auth_service.token_expires_minutes(),
        user_id=user.id,
        organization_id=user.organization_id,
        department_id=user.department_id,
        role=user.role.role_code,
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
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc
    return MessageResponse(message="Password updated.")


@router.post("/forgot-password", response_model=MessageResponse)
async def forgot_password(
    body: ForgotPasswordRequest,
    db: AsyncSession = Depends(get_db),
) -> MessageResponse:
    message, _ = await auth_service.request_password_reset(
        db,
        email=str(body.email),
        organization_code=body.organization_code,
    )
    return MessageResponse(message=message)


@router.post("/reset-password", response_model=MessageResponse)
async def reset_password(
    body: ResetPasswordRequest,
    db: AsyncSession = Depends(get_db),
) -> MessageResponse:
    try:
        await auth_service.reset_password(
            db, token=body.token, new_password=body.new_password
        )
    except auth_service.AuthError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc
    return MessageResponse(message="Password has been reset. You can log in now.")


@router.post("/activate", response_model=MessageResponse)
async def activate_account(
    body: ActivateAccountRequest,
    db: AsyncSession = Depends(get_db),
) -> MessageResponse:
    """Activate INVITED TPO or HOD (set password). Then use POST /auth/login."""
    try:
        await auth_service.activate_invited_user(
            db, token=body.token, new_password=body.new_password
        )
    except auth_service.AuthError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc
    return MessageResponse(message="Account activated. You can log in now.")


@router.post("/activate-hod", response_model=MessageResponse)
async def activate_hod(
    body: ActivateAccountRequest,
    db: AsyncSession = Depends(get_db),
) -> MessageResponse:
    """FE contract alias: POST /auth/activate-hod → same as /auth/activate."""
    try:
        user = await auth_service.activate_invited_user(
            db, token=body.token, new_password=body.new_password
        )
        await auth_service.audit_hod_activate(db, user)
    except auth_service.AuthError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc
    return MessageResponse(
        message="Password set. You can log in to the Organization Portal."
    )


@router.post("/activate-student", response_model=MessageResponse)
async def activate_student(
    body: ActivateAccountRequest,
    db: AsyncSession = Depends(get_db),
) -> MessageResponse:
    """FE: /studentportal/set-password → POST /auth/activate-student."""
    try:
        await auth_service.activate_invited_user(
            db, token=body.token, new_password=body.new_password
        )
    except auth_service.AuthError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc
    return MessageResponse(
        message="Password set. You can log in to the Student Portal."
    )

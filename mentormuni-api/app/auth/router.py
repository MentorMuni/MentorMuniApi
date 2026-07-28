"""
Auth routes.

POST /auth/login
POST /auth/logout
GET  /auth/me
POST /auth/change-password
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import service as auth_service
from app.auth.schemas import (
    ChangePasswordRequest,
    LoginRequest,
    MeResponse,
    MessageResponse,
    TokenResponse,
)
from app.common.deps import get_current_active_user, get_db, require_api_key
from app.common.security.jwt import create_access_token
from app.models.user import User

router = APIRouter(
    prefix="/auth",
    tags=["Auth"],
    dependencies=[Depends(require_api_key)],
)


def _to_me(user: User) -> MeResponse:
    return MeResponse(
        id=user.id,
        organization_id=user.organization_id,
        organization_code=user.organization.code,
        organization_type=user.organization.organization_type,
        department_id=user.department_id,
        department_code=user.department.code if user.department else None,
        role_code=user.role.role_code,
        role_name=user.role.role_name,
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

    token = create_access_token(
        user_id=user.id,
        scope="tenant",
        extra={
            "role": user.role.role_code,
            "org_id": user.organization_id,
        },
    )
    return TokenResponse(
        access_token=token,
        expires_in_minutes=auth_service.token_expires_minutes(),
    )


@router.post("/logout", response_model=MessageResponse)
async def logout(
    _user: User = Depends(get_current_active_user),
) -> MessageResponse:
    # JWT is stateless — frontend deletes the token. Endpoint exists for UX symmetry.
    return MessageResponse(message="Logged out. Discard the access token on the client.")


@router.get("/me", response_model=MeResponse)
async def me(user: User = Depends(get_current_active_user)) -> MeResponse:
    return _to_me(user)


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

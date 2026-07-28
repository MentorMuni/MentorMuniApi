"""
User routes.

POST /users                 create (platform TPO, TPO→HOD, student self-register)
GET  /users
PUT  /users/{id}
PUT  /users/{id}/approve
PUT  /users/{id}/reject
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.deps import get_current_active_user, get_db, require_api_key
from app.common.security.jwt import decode_access_token
from app.models.enums import RoleCode
from app.models.user import User
from app.users import service as user_service
from app.users.schemas import UserCreate, UserListResponse, UserResponse, UserUpdate

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
        approved_by=user.approved_by,
        approved_at=user.approved_at,
        created_at=user.created_at,
        updated_at=user.updated_at,
    )


async def _optional_user(
    credentials: HTTPAuthorizationCredentials | None,
    db: AsyncSession,
) -> User | None:
    """Return current user if Bearer token present; else None (platform / self-register)."""
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


@router.post("", response_model=UserResponse, status_code=201)
async def create_user(
    body: UserCreate,
    db: AsyncSession = Depends(get_db),
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
) -> UserResponse:
    actor = await _optional_user(credentials, db)

    # Platform creates TPO without JWT. Self-register students also without JWT.
    # TPO creating HOD requires JWT.
    if body.role_code == RoleCode.ORG_ADMIN.value and actor is not None:
        raise HTTPException(status_code=403, detail="ORG_ADMIN must be created by platform (API key only).")

    if body.role_code == RoleCode.DEPARTMENT_ADMIN.value and actor is None:
        raise HTTPException(status_code=401, detail="Login as TPO required to create HOD.")

    try:
        user = await user_service.create_user(
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
        )
    except user_service.UserServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc
    return _to_response(user)


@router.get("", response_model=UserListResponse)
async def list_users(
    department_id: int | None = Query(default=None),
    status: str | None = Query(default=None),
    role_code: str | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_active_user),
) -> UserListResponse:
    org_id = user.organization_id
    dept_filter = department_id

    # HOD is scoped to their department
    if user.role.role_code == RoleCode.DEPARTMENT_ADMIN.value:
        dept_filter = user.department_id
    elif user.role.role_code == RoleCode.STUDENT.value:
        raise HTTPException(status_code=403, detail="Students cannot list users.")

    items, total = await user_service.list_users(
        db,
        organization_id=org_id,
        department_id=dept_filter,
        status=status,
        role_code=role_code,
    )
    return UserListResponse(items=[_to_response(u) for u in items], total=total)


@router.put("/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: int,
    body: UserUpdate,
    db: AsyncSession = Depends(get_db),
    actor: User = Depends(get_current_active_user),
) -> UserResponse:
    try:
        target = await user_service.get_user(db, user_id)
        if target.organization_id != actor.organization_id:
            raise HTTPException(status_code=403, detail="Cannot update user in another org.")
        if actor.role.role_code == RoleCode.STUDENT.value and actor.id != user_id:
            raise HTTPException(status_code=403, detail="Students can only update themselves.")
        if actor.role.role_code == RoleCode.STUDENT.value and body.status is not None:
            raise HTTPException(status_code=403, detail="Students cannot change status.")

        user = await user_service.update_user(
            db,
            user_id,
            **body.model_dump(exclude_unset=True),
        )
    except user_service.UserServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc
    return _to_response(user)


@router.put("/{user_id}/approve", response_model=UserResponse)
async def approve_user(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    actor: User = Depends(get_current_active_user),
) -> UserResponse:
    try:
        user = await user_service.approve_user(db, user_id=user_id, approver=actor)
    except user_service.UserServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc
    return _to_response(user)


@router.put("/{user_id}/reject", response_model=UserResponse)
async def reject_user(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    actor: User = Depends(get_current_active_user),
) -> UserResponse:
    try:
        user = await user_service.reject_user(db, user_id=user_id, approver=actor)
    except user_service.UserServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc
    return _to_response(user)

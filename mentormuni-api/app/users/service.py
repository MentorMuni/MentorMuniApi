"""User create / list / approve / reject service."""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.common.security.passwords import hash_password
from app.models.department import Department
from app.models.enums import OrganizationType, RoleCode, UserStatus
from app.models.organization import Organization
from app.models.role import Role
from app.models.user import User
from app.users.rules import UserRuleError, validate_department_for_role

PUBLIC_ORG_CODE = "PUBLIC"


class UserServiceError(Exception):
    def __init__(self, message: str, *, status_code: int = 400) -> None:
        super().__init__(message)
        self.message = message
        self.status_code = status_code


async def _get_role_by_code(db: AsyncSession, role_code: str) -> Role:
    result = await db.execute(select(Role).where(Role.role_code == role_code))
    role = result.scalar_one_or_none()
    if role is None:
        raise UserServiceError(f"Unknown role_code: {role_code}", status_code=400)
    return role


async def _get_org(
    db: AsyncSession,
    *,
    organization_id: int | None,
    organization_code: str | None,
) -> Organization:
    if organization_id is not None:
        org = await db.get(Organization, organization_id)
    elif organization_code:
        result = await db.execute(
            select(Organization).where(Organization.code == organization_code.upper())
        )
        org = result.scalar_one_or_none()
    else:
        raise UserServiceError("organization_id or organization_code is required.")

    if org is None:
        raise UserServiceError("Organization not found.", status_code=404)
    return org


async def create_user(
    db: AsyncSession,
    *,
    first_name: str,
    last_name: str,
    email: str,
    username: str,
    password: str,
    role_code: str,
    organization_id: int | None = None,
    organization_code: str | None = None,
    department_id: int | None = None,
    mobile: str | None = None,
    individual: bool = False,
    created_by: User | None = None,
) -> User:
    # B2C individual student → always PUBLIC org, ACTIVE, no department.
    if individual:
        role_code = RoleCode.STUDENT.value
        organization_code = PUBLIC_ORG_CODE
        organization_id = None
        department_id = None

    org = await _get_org(
        db,
        organization_id=organization_id,
        organization_code=organization_code,
    )
    role = await _get_role_by_code(db, role_code)

    try:
        validate_department_for_role(
            role_code=role.role_code,
            organization_type=org.organization_type,
            department_id=department_id,
        )
    except UserRuleError as exc:
        raise UserServiceError(str(exc)) from exc

    if department_id is not None:
        dept = await db.get(Department, department_id)
        if dept is None or dept.organization_id != org.id:
            raise UserServiceError(
                "department_id does not belong to this organization.",
                status_code=400,
            )

    email_norm = email.lower().strip()
    username_norm = username.strip()

    dup = await db.execute(
        select(User).where(
            User.organization_id == org.id,
            (User.email == email_norm) | (User.username == username_norm),
        )
    )
    if dup.scalar_one_or_none():
        raise UserServiceError(
            "Email or username already exists in this organization.",
            status_code=409,
        )

    # Status rules
    if individual or org.organization_type == OrganizationType.PUBLIC.value:
        status = UserStatus.ACTIVE.value
    elif role.role_code == RoleCode.STUDENT.value:
        status = UserStatus.PENDING.value
    else:
        # TPO / HOD created by platform or TPO → ACTIVE immediately
        status = UserStatus.ACTIVE.value

    # Permission checks when an authenticated actor creates someone
    if created_by is not None:
        actor_role = created_by.role.role_code
        if role.role_code == RoleCode.ORG_ADMIN.value:
            # Only platform (no JWT actor) should create TPO — created_by None.
            # If somehow called with actor, deny unless same org bootstrap not needed.
            raise UserServiceError("ORG_ADMIN can only be created by platform (API key).", status_code=403)
        if actor_role == RoleCode.ORG_ADMIN.value:
            if created_by.organization_id != org.id:
                raise UserServiceError("Cannot create users in another organization.", status_code=403)
            if role.role_code not in {
                RoleCode.DEPARTMENT_ADMIN.value,
                RoleCode.STUDENT.value,
            }:
                raise UserServiceError("ORG_ADMIN can only create HOD or Student.", status_code=403)
        elif actor_role == RoleCode.DEPARTMENT_ADMIN.value:
            raise UserServiceError("HOD cannot create users directly.", status_code=403)
        elif actor_role == RoleCode.STUDENT.value:
            raise UserServiceError("Students cannot create users.", status_code=403)

    user = User(
        organization_id=org.id,
        department_id=department_id,
        role_id=role.id,
        first_name=first_name.strip(),
        last_name=last_name.strip(),
        email=email_norm,
        mobile=mobile,
        username=username_norm,
        password_hash=hash_password(password),
        status=status,
    )
    db.add(user)
    await db.flush()

    result = await db.execute(
        select(User)
        .where(User.id == user.id)
        .options(selectinload(User.role), selectinload(User.organization), selectinload(User.department))
    )
    return result.scalar_one()


async def list_users(
    db: AsyncSession,
    *,
    organization_id: int,
    department_id: int | None = None,
    status: str | None = None,
    role_code: str | None = None,
) -> tuple[list[User], int]:
    stmt = (
        select(User)
        .join(Role, User.role_id == Role.id)
        .where(User.organization_id == organization_id)
        .options(selectinload(User.role), selectinload(User.department))
    )
    count_stmt = (
        select(func.count())
        .select_from(User)
        .join(Role, User.role_id == Role.id)
        .where(User.organization_id == organization_id)
    )

    if department_id is not None:
        stmt = stmt.where(User.department_id == department_id)
        count_stmt = count_stmt.where(User.department_id == department_id)
    if status:
        stmt = stmt.where(User.status == status)
        count_stmt = count_stmt.where(User.status == status)
    if role_code:
        stmt = stmt.where(Role.role_code == role_code)
        count_stmt = count_stmt.where(Role.role_code == role_code)

    stmt = stmt.order_by(User.id.desc())
    items = list((await db.execute(stmt)).scalars().unique().all())
    total = int((await db.execute(count_stmt)).scalar_one())
    return items, total


async def get_user(db: AsyncSession, user_id: int) -> User:
    result = await db.execute(
        select(User)
        .where(User.id == user_id)
        .options(selectinload(User.role), selectinload(User.organization), selectinload(User.department))
    )
    user = result.scalar_one_or_none()
    if user is None:
        raise UserServiceError("User not found.", status_code=404)
    return user


async def update_user(db: AsyncSession, user_id: int, **fields: object) -> User:
    user = await get_user(db, user_id)
    for key, value in fields.items():
        if value is None and key not in {"mobile", "department_id"}:
            continue
        setattr(user, key, value)
    await db.flush()
    return await get_user(db, user_id)


async def approve_user(db: AsyncSession, *, user_id: int, approver: User) -> User:
    user = await get_user(db, user_id)
    if user.organization_id != approver.organization_id:
        raise UserServiceError("Cannot approve user from another organization.", status_code=403)
    if user.role.role_code != RoleCode.STUDENT.value:
        raise UserServiceError("Only students can be approved.", status_code=400)
    if user.status != UserStatus.PENDING.value:
        raise UserServiceError(f"User is {user.status}, not PENDING.", status_code=400)

    # HOD can only approve students in their department
    if approver.role.role_code == RoleCode.DEPARTMENT_ADMIN.value:
        if user.department_id != approver.department_id:
            raise UserServiceError("HOD can only approve students in their department.", status_code=403)
    elif approver.role.role_code != RoleCode.ORG_ADMIN.value:
        raise UserServiceError("Only HOD or TPO can approve students.", status_code=403)

    user.status = UserStatus.ACTIVE.value
    user.approved_by = approver.id
    user.approved_at = datetime.now(timezone.utc)
    await db.flush()
    return await get_user(db, user_id)


async def reject_user(db: AsyncSession, *, user_id: int, approver: User) -> User:
    user = await get_user(db, user_id)
    if user.organization_id != approver.organization_id:
        raise UserServiceError("Cannot reject user from another organization.", status_code=403)
    if user.role.role_code != RoleCode.STUDENT.value:
        raise UserServiceError("Only students can be rejected.", status_code=400)
    if user.status != UserStatus.PENDING.value:
        raise UserServiceError(f"User is {user.status}, not PENDING.", status_code=400)

    if approver.role.role_code == RoleCode.DEPARTMENT_ADMIN.value:
        if user.department_id != approver.department_id:
            raise UserServiceError("HOD can only reject students in their department.", status_code=403)
    elif approver.role.role_code != RoleCode.ORG_ADMIN.value:
        raise UserServiceError("Only HOD or TPO can reject students.", status_code=403)

    user.status = UserStatus.REJECTED.value
    user.approved_by = approver.id
    user.approved_at = datetime.now(timezone.utc)
    await db.flush()
    return await get_user(db, user_id)

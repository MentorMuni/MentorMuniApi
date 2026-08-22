"""User create / list / approve / reject / invite / import service."""

from __future__ import annotations

import csv
import hashlib
import io
import logging
import secrets
from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.common.audit import write_audit
from app.common.email.exceptions import EmailError
from app.common.email.flows import send_staff_activation_email
from app.common.email.templates import build_hod_activation_url
from app.common.organization_access import (
    OrganizationAccessError,
    ensure_organization_accepts_registration,
)
from app.common.security.passwords import hash_password
from app.models.department import Department
from app.models.enums import OrganizationType, RoleCode, UserStatus
from app.models.organization import Organization
from app.models.role import Role
from app.models.user import User
from app.users.rules import UserRuleError, validate_department_for_role

logger = logging.getLogger(__name__)

PUBLIC_ORG_CODE = "PUBLIC"


class UserServiceError(Exception):
    def __init__(self, message: str, *, status_code: int = 400, code: str | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.code = code


def _hash_token(raw: str) -> str:
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


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


async def _reload_user(db: AsyncSession, user_id: int) -> User:
    result = await db.execute(
        select(User)
        .where(User.id == user_id)
        .where(User.deleted_at.is_(None))
        .options(
            selectinload(User.role),
            selectinload(User.organization),
            selectinload(User.department),
        )
    )
    user = result.scalar_one_or_none()
    if user is None:
        raise UserServiceError("User not found.", status_code=404)
    return user


async def create_user(
    db: AsyncSession,
    *,
    first_name: str,
    last_name: str,
    email: str,
    username: str,
    password: str | None = None,
    role_code: str,
    organization_id: int | None = None,
    organization_code: str | None = None,
    department_id: int | None = None,
    mobile: str | None = None,
    individual: bool = False,
    created_by: User | None = None,
    activation_hours: int = 72,
    roll_number: str | None = None,
    batch_year: int | None = None,
    invite_without_password: bool = False,
    auto_enroll: bool = False,
    dept_admin_title: str | None = None,
) -> tuple[User, str | None, datetime | None]:
    """
    Returns (user, raw_activation_token|None, expires|None).

    Status rules:
    - HOD (no password) → INVITED + activation token
    - Student + auto_enroll (staff add) → INVITED + activation token
    - Student without auto_enroll (staff) → PENDING (approval queue)
    - Self-register without password → PENDING
    """
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

    try:
        ensure_organization_accepts_registration(org)
    except OrganizationAccessError as exc:
        raise UserServiceError(exc.message, status_code=exc.status_code) from exc

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
        if dept is None or dept.organization_id != org.id or dept.deleted_at is not None:
            raise UserServiceError(
                "department_id does not belong to this organization.",
                status_code=400,
            )

    email_norm = email.lower().strip()
    username_norm = username.strip()

    dup = await db.execute(
        select(User).where(
            User.organization_id == org.id,
            User.deleted_at.is_(None),
            (User.email == email_norm) | (User.username == username_norm),
        )
    )
    if dup.scalar_one_or_none():
        raise UserServiceError(
            "Email or username already exists in this organization.",
            status_code=409,
            code="HOD_EMAIL_CONFLICT",
        )

    invite_hod = (
        role.role_code == RoleCode.DEPARTMENT_ADMIN.value
        and created_by is not None
        and not password
    )
    invite_student = (
        role.role_code == RoleCode.STUDENT.value
        and created_by is not None
        and (not password or invite_without_password)
    )
    self_enroll_no_password = (
        role.role_code == RoleCode.STUDENT.value
        and created_by is None
        and not password
    )

    if individual or org.organization_type == OrganizationType.PUBLIC.value:
        status = UserStatus.ACTIVE.value
        needs_activation_token = False
    elif invite_hod:
        status = UserStatus.INVITED.value
        needs_activation_token = True
    elif invite_student and auto_enroll:
        # Staff add with auto_enroll → roster immediately (INVITED + setup link)
        status = UserStatus.INVITED.value
        needs_activation_token = True
    elif invite_student or self_enroll_no_password or role.role_code == RoleCode.STUDENT.value:
        # PENDING queue (self-register or staff without auto_enroll)
        status = UserStatus.PENDING.value
        needs_activation_token = False
    else:
        status = UserStatus.ACTIVE.value
        needs_activation_token = False

    if created_by is not None:
        actor_role = created_by.role.role_code
        if role.role_code == RoleCode.ORG_ADMIN.value:
            raise UserServiceError(
                "ORG_ADMIN can only be created by platform (API key).",
                status_code=403,
            )
        if actor_role == RoleCode.ORG_ADMIN.value:
            if created_by.organization_id != org.id:
                raise UserServiceError(
                    "Cannot create users in another organization.",
                    status_code=403,
                )
            if role.role_code not in {
                RoleCode.DEPARTMENT_ADMIN.value,
                RoleCode.STUDENT.value,
            }:
                raise UserServiceError(
                    "ORG_ADMIN can only create HOD or Student.",
                    status_code=403,
                )
        elif actor_role == RoleCode.DEPARTMENT_ADMIN.value:
            if role.role_code != RoleCode.STUDENT.value:
                raise UserServiceError("HOD can only enroll students.", status_code=403)
            if created_by.organization_id != org.id:
                raise UserServiceError(
                    "Cannot create users in another organization.",
                    status_code=403,
                )
            if department_id != created_by.department_id:
                raise UserServiceError(
                    "HOD can only enroll students in their own department.",
                    status_code=403,
                )
        elif actor_role == RoleCode.STUDENT.value:
            raise UserServiceError("Students cannot create users.", status_code=403)

    if needs_activation_token:
        raw_token = secrets.token_urlsafe(32)
        expires = datetime.now(timezone.utc) + timedelta(hours=activation_hours)
        password_hash = None
        activation_hash = _hash_token(raw_token)
    elif status == UserStatus.ACTIVE.value:
        if not password:
            raise UserServiceError("password is required for this role/status.", status_code=422)
        password_hash = hash_password(password)
        raw_token = None
        expires = None
        activation_hash = None
    else:
        # PENDING — no token until approve
        password_hash = hash_password(password) if password else None
        raw_token = None
        expires = None
        activation_hash = None

    user = User(
        organization_id=org.id,
        department_id=department_id,
        role_id=role.id,
        first_name=first_name.strip(),
        last_name=last_name.strip(),
        email=email_norm,
        mobile=mobile,
        username=username_norm,
        password_hash=password_hash,
        status=status,
        activation_token_hash=activation_hash,
        activation_expires_at=expires,
        must_change_password=False,
        roll_number=(roll_number.strip() if roll_number else None),
        batch_year=batch_year,
        dept_admin_title=(
            dept_admin_title
            if role.role_code == RoleCode.DEPARTMENT_ADMIN.value
            else None
        ),
    )
    db.add(user)
    await db.flush()

    if created_by is not None:
        await write_audit(
            db,
            organization_id=org.id,
            actor_user_id=created_by.id,
            action="USER_CREATE",
            entity_type="user",
            entity_id=user.id,
            payload={"role_code": role.role_code, "status": status, "auto_enroll": auto_enroll},
        )

    return await _reload_user(db, user.id), raw_token, expires


async def register_student(
    db: AsyncSession,
    *,
    email: str,
    department_id: int,
    organization_id: int | None = None,
    organization_code: str | None = None,
    name: str | None = None,
    first_name: str | None = None,
    last_name: str | None = None,
    username: str | None = None,
    password: str | None = None,
    mobile: str | None = None,
    phone: str | None = None,
    roll_number: str | None = None,
    batch_year: int | None = None,
) -> tuple[User, bool]:
    """
    Public self-enroll → PENDING.

    Password is ignored: college enroll never sets credentials. HOD/TPO approve
    always issues a set-password link (INVITED). Returns (user, created).
    created=False when idempotent re-submit of same PENDING email.
    """
    import re
    import secrets as _secrets

    # C4: never accept a password on public self-enroll (prevents post-approve hijack).
    password = None

    email_norm = email.lower().strip()
    contact = (phone or mobile or "").strip() or None

    if name and not (first_name and last_name):
        parts = [p for p in re.split(r"\s+", name.strip()) if p]
        if not parts:
            first_name, last_name = "Student", "User"
        elif len(parts) == 1:
            first_name, last_name = parts[0], "User"
        else:
            first_name, last_name = parts[0], " ".join(parts[1:])
    first_name = (first_name or "Student").strip()[:128]
    last_name = (last_name or "User").strip()[:128]

    if not organization_id and not organization_code:
        raise UserServiceError(
            "organization_code or organization_id is required.",
            status_code=422,
        )

    org = await _get_org(
        db,
        organization_id=organization_id,
        organization_code=organization_code,
    )
    if org.organization_type == OrganizationType.PUBLIC.value:
        raise UserServiceError(
            "Use individual signup for MentorMuni Public. College students must pick a college.",
            status_code=400,
        )

    # Idempotent: same email already pending in this org → return existing
    existing = await db.execute(
        select(User)
        .where(User.organization_id == org.id)
        .where(User.email == email_norm)
        .where(User.deleted_at.is_(None))
        .options(
            selectinload(User.role),
            selectinload(User.organization),
            selectinload(User.department),
        )
    )
    prior = existing.scalar_one_or_none()
    if prior is not None:
        if prior.role.role_code != RoleCode.STUDENT.value:
            raise UserServiceError(
                "Email already belongs to another account in this organization.",
                status_code=409,
            )
        if prior.status == UserStatus.PENDING.value:
            # Refresh contact / roll if provided
            changed = False
            if contact and prior.mobile != contact:
                prior.mobile = contact
                changed = True
            if roll_number and prior.roll_number != roll_number.strip():
                prior.roll_number = roll_number.strip()
                changed = True
            if batch_year is not None and prior.batch_year != batch_year:
                prior.batch_year = batch_year
                changed = True
            if department_id and prior.department_id != department_id:
                prior.department_id = department_id
                changed = True
            if changed:
                await db.flush()
                prior = await get_user(db, prior.id)
            return prior, False
        raise UserServiceError(
            "This email is already enrolled or approved. Log in or use forgot password.",
            status_code=409,
        )

    username_norm = (username or "").strip()
    if not username_norm:
        local = re.sub(r"[^a-z0-9._-]+", "", email_norm.split("@", 1)[0].lower()) or "student"
        username_norm = local[:100]

    try:
        user, _, _ = await create_user(
            db,
            first_name=first_name,
            last_name=last_name,
            email=email_norm,
            username=username_norm,
            password=None,
            role_code=RoleCode.STUDENT.value,
            organization_id=org.id,
            department_id=department_id,
            mobile=contact,
            individual=False,
            created_by=None,
            roll_number=roll_number,
            batch_year=batch_year,
            invite_without_password=True,
        )
    except UserServiceError as exc:
        if exc.status_code == 409 and not username:
            user, _, _ = await create_user(
                db,
                first_name=first_name,
                last_name=last_name,
                email=email_norm,
                username=f"{username_norm}.{_secrets.token_hex(2)}",
                password=None,
                role_code=RoleCode.STUDENT.value,
                organization_id=org.id,
                department_id=department_id,
                mobile=contact,
                individual=False,
                created_by=None,
                roll_number=roll_number,
                batch_year=batch_year,
                invite_without_password=True,
            )
        else:
            raise

    await write_audit(
        db,
        organization_id=org.id,
        actor_user_id=None,
        action="student.self_register",
        entity_type="user",
        entity_id=user.id,
        payload={"department_id": department_id, "source": "self_enroll"},
    )
    return user, True


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
        .where(User.deleted_at.is_(None))
        .options(selectinload(User.role), selectinload(User.department))
    )
    count_stmt = (
        select(func.count())
        .select_from(User)
        .join(Role, User.role_id == Role.id)
        .where(User.organization_id == organization_id)
        .where(User.deleted_at.is_(None))
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
    return await _reload_user(db, user_id)


async def update_user(db: AsyncSession, user_id: int, **fields: object) -> User:
    user = await get_user(db, user_id)
    for key, value in fields.items():
        if value is None and key not in {"mobile", "department_id", "roll_number", "batch_year"}:
            continue
        setattr(user, key, value)
    await db.flush()
    return await get_user(db, user_id)


async def soft_delete_user(
    db: AsyncSession,
    *,
    user_id: int,
    actor: User,
) -> User:
    user = await get_user(db, user_id)
    if user.organization_id != actor.organization_id:
        raise UserServiceError("Cannot delete user in another organization.", status_code=403)
    if user.id == actor.id:
        raise UserServiceError("Cannot delete your own account.", status_code=400)
    if user.role.role_code == RoleCode.ORG_ADMIN.value:
        raise UserServiceError("Cannot delete ORG_ADMIN via this API.", status_code=403)

    user.deleted_at = datetime.now(timezone.utc)
    user.status = UserStatus.BLOCKED.value
    await write_audit(
        db,
        organization_id=actor.organization_id,
        actor_user_id=actor.id,
        action="USER_SOFT_DELETE",
        entity_type="user",
        entity_id=user.id,
    )
    await db.flush()
    return user


async def approve_user(
    db: AsyncSession,
    *,
    user_id: int,
    approver: User,
    activation_hours: int = 72,
    send_password_email: bool = True,
) -> tuple[User, str | None, str | None, bool]:
    """
    Approve PENDING student.

    Returns (user, raw_token|None, setup_url|None, email_sent).
    - If student already has a password → ACTIVE.
    - If no password → INVITED + activation token + set-password email.
    """
    user = await get_user(db, user_id)
    if user.organization_id != approver.organization_id:
        raise UserServiceError("Cannot approve user from another organization.", status_code=403)
    if user.role.role_code != RoleCode.STUDENT.value:
        raise UserServiceError("Only students can be approved.", status_code=400)
    if user.status != UserStatus.PENDING.value:
        raise UserServiceError(f"User is {user.status}, not PENDING.", status_code=400)

    if approver.role.role_code == RoleCode.DEPARTMENT_ADMIN.value:
        if user.department_id != approver.department_id:
            raise UserServiceError(
                "HOD can only approve students in their department.",
                status_code=403,
            )
    elif approver.role.role_code != RoleCode.ORG_ADMIN.value:
        raise UserServiceError("Only HOD or TPO can approve students.", status_code=403)

    user.approved_by = approver.id
    user.approved_at = datetime.now(timezone.utc)

    raw_token: str | None = None
    setup_url: str | None = None
    email_sent = False

    # Always INVITED + set-password — never activate from a pre-set enroll password.
    user.password_hash = None
    raw_token = secrets.token_urlsafe(32)
    expires = datetime.now(timezone.utc) + timedelta(hours=activation_hours)
    user.status = UserStatus.INVITED.value
    user.activation_token_hash = _hash_token(raw_token)
    user.activation_expires_at = expires
    setup_url = build_student_activation_url(raw_token)
    if send_password_email:
        email_sent = await send_student_set_password_email(
            user=user, raw_token=raw_token, expires=expires
        )

    await write_audit(
        db,
        organization_id=approver.organization_id,
        actor_user_id=approver.id,
        action="student.approve",
        entity_type="user",
        entity_id=user.id,
        payload={"email_sent": email_sent, "needs_password": True},
    )
    await db.flush()
    user = await get_user(db, user.id)
    # Return token only when email failed (ops fallback).
    if email_sent:
        return user, None, None, email_sent
    return user, raw_token, setup_url, email_sent


async def reject_user(
    db: AsyncSession,
    *,
    user_id: int,
    approver: User,
    send_email: bool = True,
) -> tuple[User, bool]:
    """
    Reject PENDING student.

    Returns (user, email_sent).
    """
    user = await get_user(db, user_id)
    if user.organization_id != approver.organization_id:
        raise UserServiceError("Cannot reject user from another organization.", status_code=403)
    if user.role.role_code != RoleCode.STUDENT.value:
        raise UserServiceError("Only students can be rejected.", status_code=400)
    if user.status != UserStatus.PENDING.value:
        raise UserServiceError(f"User is {user.status}, not PENDING.", status_code=400)

    if approver.role.role_code == RoleCode.DEPARTMENT_ADMIN.value:
        if user.department_id != approver.department_id:
            raise UserServiceError(
                "HOD can only reject students in their department.",
                status_code=403,
            )
    elif approver.role.role_code != RoleCode.ORG_ADMIN.value:
        raise UserServiceError("Only HOD or TPO can reject students.", status_code=403)

    user.status = UserStatus.REJECTED.value
    user.approved_by = approver.id
    user.approved_at = datetime.now(timezone.utc)

    email_sent = False
    if send_email:
        email_sent = await send_student_enrollment_denied_email(user=user)

    await write_audit(
        db,
        organization_id=approver.organization_id,
        actor_user_id=approver.id,
        action="student.reject",
        entity_type="user",
        entity_id=user.id,
        payload={"email_sent": email_sent},
    )
    await db.flush()
    return await get_user(db, user_id), email_sent


async def send_student_set_password_email(
    *,
    user: User,
    raw_token: str,
    expires: datetime,
) -> bool:
    from app.common.email.flows import send_student_activation_email

    try:
        result = await send_student_activation_email(
            to_email=user.email,
            first_name=user.first_name,
            last_name=user.last_name,
            username=user.username,
            organization_name=user.organization.name,
            department_name=user.department.name if user.department else None,
            raw_token=raw_token,
            expires_at=expires,
        )
        return bool(getattr(result, "sent", False))
    except EmailError as exc:
        logger.warning("student_set_password_email_failed to=%s err=%s", user.email, exc)
        return False


async def send_student_enrollment_denied_email(*, user: User) -> bool:
    from app.common.email.flows import send_student_enrollment_denied_email as _send

    try:
        result = await _send(
            to_email=user.email,
            first_name=user.first_name,
            last_name=user.last_name,
            organization_name=user.organization.name,
            department_name=user.department.name if user.department else None,
        )
        return bool(getattr(result, "sent", False))
    except EmailError as exc:
        logger.warning("student_enrollment_denied_email_failed to=%s err=%s", user.email, exc)
        return False


def build_student_activation_url(raw_token: str) -> str:
    from app.common.email.templates import build_student_activation_url as _build

    return _build(raw_token)


async def issue_student_activation(
    db: AsyncSession,
    *,
    user: User,
    actor: User | None = None,
    activation_hours: int = 72,
    send_email: bool = True,
) -> tuple[User, str | None, str | None, bool]:
    """Rotate set-password token for INVITED/ACTIVE student (not BLOCKED/REJECTED)."""
    if user.role.role_code != RoleCode.STUDENT.value:
        raise UserServiceError("Only students can receive set-password links.", status_code=400)
    if user.status == UserStatus.BLOCKED.value:
        raise UserServiceError(
            "Student is blocked. Unblock before sending a set-password link.",
            status_code=400,
        )
    if user.status == UserStatus.REJECTED.value:
        raise UserServiceError(
            "Student was rejected. Re-invite or ask them to enroll again.",
            status_code=400,
        )

    raw_token = secrets.token_urlsafe(32)
    expires = datetime.now(timezone.utc) + timedelta(hours=activation_hours)
    user.status = UserStatus.INVITED.value
    user.password_hash = None
    user.activation_token_hash = _hash_token(raw_token)
    user.activation_expires_at = expires
    await db.flush()
    user = await get_user(db, user.id)

    email_sent = False
    setup_url = build_student_activation_url(raw_token)
    if send_email:
        email_sent = await send_student_set_password_email(
            user=user, raw_token=raw_token, expires=expires
        )

    if actor is not None:
        await write_audit(
            db,
            organization_id=user.organization_id,
            actor_user_id=actor.id,
            action="student.set_password_link",
            entity_type="user",
            entity_id=user.id,
            payload={"email_sent": email_sent},
        )

    return (
        user,
        (None if email_sent else raw_token),
        (None if email_sent else setup_url),
        email_sent,
    )


async def import_students_csv(
    db: AsyncSession,
    *,
    actor: User,
    csv_text: str,
) -> tuple[list[User], int, int, list[str]]:
    """
    CSV headers: first_name,last_name,email,username,password,department_id[,mobile]
    Creates STUDENT users as PENDING in actor's organization.
    """
    reader = csv.DictReader(io.StringIO(csv_text))
    if not reader.fieldnames:
        raise UserServiceError("CSV is empty or missing headers.", status_code=422)

    required = {"first_name", "last_name", "email", "username", "password", "department_id"}
    missing = required - {h.strip().lower() for h in reader.fieldnames}
    # normalize fieldnames
    field_map = {h.strip().lower(): h for h in reader.fieldnames}
    if missing - set(field_map.keys()):
        raise UserServiceError(
            f"CSV missing columns: {', '.join(sorted(missing - set(field_map.keys())))}",
            status_code=422,
        )

    created: list[User] = []
    skipped = 0
    errors: list[str] = []

    for i, row in enumerate(reader, start=2):
        def _cell(key: str) -> str:
            raw_key = field_map.get(key, key)
            return (row.get(raw_key) or "").strip()

        try:
            dept_raw = _cell("department_id")
            if not dept_raw.isdigit():
                raise UserServiceError(f"Row {i}: department_id must be an integer.")
            user, _, _ = await create_user(
                db,
                first_name=_cell("first_name"),
                last_name=_cell("last_name"),
                email=_cell("email"),
                username=_cell("username"),
                password=_cell("password"),
                role_code=RoleCode.STUDENT.value,
                organization_id=actor.organization_id,
                department_id=int(dept_raw),
                mobile=_cell("mobile") or None,
                created_by=actor,
            )
            created.append(user)
        except UserServiceError as exc:
            if exc.status_code == 409:
                skipped += 1
                errors.append(f"Row {i}: skipped duplicate — {exc.message}")
            else:
                errors.append(f"Row {i}: {exc.message}")
        except Exception as exc:  # noqa: BLE001
            errors.append(f"Row {i}: {exc}")

    await write_audit(
        db,
        organization_id=actor.organization_id,
        actor_user_id=actor.id,
        action="USER_IMPORT",
        entity_type="user",
        entity_id=None,
        payload={"created": len(created), "skipped": skipped, "errors": len(errors)},
    )
    return created, skipped, len(errors), errors


async def send_hod_invite_email(
    *,
    user: User,
    raw_token: str,
    expires: datetime,
    role_label: str | None = None,
) -> bool:
    label = role_label or "HOD (Department Admin)"
    try:
        await send_staff_activation_email(
            to_email=user.email,
            first_name=user.first_name,
            last_name=user.last_name,
            username=user.username,
            organization_name=user.organization.name,
            role_label=label,
            raw_token=raw_token,
            expires_at=expires,
        )
        return True
    except EmailError as exc:
        logger.warning("hod_activation_email_failed to=%s err=%s", user.email, exc)
        return False


def activation_link(raw_token: str) -> str:
    return build_hod_activation_url(raw_token)

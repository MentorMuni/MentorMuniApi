"""HOD + Placement Coordinator invite / reinvite / revoke / replace for a department."""

from __future__ import annotations

import re
import secrets
from datetime import datetime, timedelta, timezone

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.common.audit import write_audit
from app.common.email.templates import build_hod_activation_url
from app.departments import service as dept_service
from app.departments.service import DepartmentError
from app.models.audit_log import AuditLog
from app.models.enums import DeptAdminTitle, RoleCode, UserStatus
from app.models.role import Role
from app.models.user import User
from app.users import service as user_service

_HOD_AUDIT_ACTIONS = (
    "hod.invite",
    "hod.reinvite",
    "hod.revoke",
    "hod.replace",
    "hod.activate",
    "coordinator.invite",
    "coordinator.reinvite",
    "coordinator.revoke",
    "coordinator.replace",
    "coordinator.activate",
)

_EVENT_MAP = {
    "hod.invite": "invited",
    "hod.reinvite": "reinvited",
    "hod.revoke": "revoked",
    "hod.replace": "replaced",
    "hod.activate": "activated",
    "coordinator.invite": "coordinator_invited",
    "coordinator.reinvite": "coordinator_reinvited",
    "coordinator.revoke": "coordinator_revoked",
    "coordinator.replace": "coordinator_replaced",
    "coordinator.activate": "coordinator_activated",
}

_TITLE_HOD = DeptAdminTitle.HOD.value
_TITLE_COORD = DeptAdminTitle.PLACEMENT_COORDINATOR.value

_LIVE = {UserStatus.INVITED.value, UserStatus.ACTIVE.value}


def _normalize_title(title: str | None) -> str:
    raw = (title or _TITLE_HOD).strip().upper()
    if raw == _TITLE_COORD:
        return _TITLE_COORD
    return _TITLE_HOD


def _title_label(title: str) -> str:
    if title == _TITLE_COORD:
        return "Placement Coordinator"
    return "HOD"


def _email_role_label(title: str) -> str:
    if title == _TITLE_COORD:
        return "Placement Coordinator (Department Admin)"
    return "HOD (Department Admin)"


def _audit_prefix(title: str) -> str:
    return "coordinator" if title == _TITLE_COORD else "hod"


def _split_name(name: str) -> tuple[str, str]:
    parts = [p for p in re.split(r"\s+", name.strip()) if p]
    if not parts:
        return "Mentor", "User"
    if len(parts) == 1:
        return parts[0], "User"
    return parts[0], " ".join(parts[1:])


def _username_from_email(email: str, department_code: str) -> str:
    local = email.split("@", 1)[0].lower()
    local = re.sub(r"[^a-z0-9._-]+", "", local) or "mentor"
    code = re.sub(r"[^a-z0-9]+", "", department_code.lower()) or "dept"
    base = f"{local}.{code}"[:100]
    return base


def _mentor_status(user: User | None) -> str:
    if user is None:
        return "unassigned"
    if user.status == UserStatus.INVITED.value:
        return "invited"
    if user.status == UserStatus.ACTIVE.value:
        return "active"
    if user.status == UserStatus.BLOCKED.value:
        return "revoked"
    return "unassigned"


def _hod_status(user: User | None) -> str:
    return _mentor_status(user)


def _title_filter(title: str):
    if title == _TITLE_COORD:
        return User.dept_admin_title == _TITLE_COORD
    return or_(User.dept_admin_title.is_(None), User.dept_admin_title == _TITLE_HOD)


async def _dept_admin_role_id(db: AsyncSession) -> int:
    return (
        await db.execute(select(Role.id).where(Role.role_code == RoleCode.DEPARTMENT_ADMIN.value))
    ).scalar_one()


async def get_mentor_by_title(
    db: AsyncSession, department_id: int, title: str
) -> User | None:
    """Prefer live mentor for title; else most recent BLOCKED for display."""
    title = _normalize_title(title)
    role_id = await _dept_admin_role_id(db)
    title_clause = _title_filter(title)

    live = await db.execute(
        select(User)
        .where(User.department_id == department_id)
        .where(User.role_id == role_id)
        .where(User.deleted_at.is_(None))
        .where(User.status.in_([UserStatus.INVITED.value, UserStatus.ACTIVE.value]))
        .where(title_clause)
        .options(selectinload(User.organization), selectinload(User.role))
        .order_by(User.created_at.desc())
        .limit(1)
    )
    user = live.scalar_one_or_none()
    if user is not None:
        return user

    revoked = await db.execute(
        select(User)
        .where(User.department_id == department_id)
        .where(User.role_id == role_id)
        .where(User.deleted_at.is_(None))
        .where(User.status == UserStatus.BLOCKED.value)
        .where(title_clause)
        .options(selectinload(User.organization), selectinload(User.role))
        .order_by(User.updated_at.desc())
        .limit(1)
    )
    return revoked.scalar_one_or_none()


async def get_current_hod(db: AsyncSession, department_id: int) -> User | None:
    return await get_mentor_by_title(db, department_id, _TITLE_HOD)


async def get_current_coordinator(db: AsyncSession, department_id: int) -> User | None:
    return await get_mentor_by_title(db, department_id, _TITLE_COORD)


async def student_count(db: AsyncSession, department_id: int) -> int:
    role_id = (
        await db.execute(select(Role.id).where(Role.role_code == RoleCode.STUDENT.value))
    ).scalar_one()
    result = await db.execute(
        select(func.count())
        .select_from(User)
        .where(User.department_id == department_id)
        .where(User.role_id == role_id)
        .where(User.deleted_at.is_(None))
        .where(
            User.status.in_(
                [
                    UserStatus.PENDING.value,
                    UserStatus.ACTIVE.value,
                    UserStatus.INVITED.value,
                ]
            )
        )
    )
    return int(result.scalar_one() or 0)


async def load_mentor_history(db: AsyncSession, dept) -> list[dict]:
    result = await db.execute(
        select(AuditLog)
        .where(AuditLog.organization_id == dept.organization_id)
        .where(AuditLog.action.in_(_HOD_AUDIT_ACTIONS))
        .where(AuditLog.entity_type == "department")
        .where(AuditLog.entity_id == dept.id)
        .order_by(AuditLog.created_at.asc())
        .limit(100)
    )
    items: list[dict] = []
    for row in result.scalars().all():
        payload = row.payload_json or {}
        items.append(
            {
                "id": str(row.id),
                "at": row.created_at,
                "event": _EVENT_MAP.get(
                    row.action,
                    row.action.replace("hod.", "").replace("coordinator.", "coordinator_"),
                ),
                "name": str(payload.get("name") or ""),
                "email": str(payload.get("email") or payload.get("new_email") or ""),
                "reason": str(payload.get("reason") or ""),
                "replaced_by_email": str(payload.get("replaced_by_email") or ""),
            }
        )
    return items


def _slot_timestamps(user: User | None, status: str) -> tuple[datetime | None, datetime | None]:
    invited_at = None
    activated_at = None
    if user is None:
        return invited_at, activated_at
    if status == "invited":
        invited_at = user.created_at
    elif status == "active":
        activated_at = user.updated_at or user.created_at
        invited_at = user.created_at
    elif status == "revoked":
        invited_at = user.created_at
    return invited_at, activated_at


async def enrich_department(
    db: AsyncSession,
    dept,
    *,
    activation_token: str | None = None,
    activation_url: str | None = None,
    emailed: bool | None = None,
    message: str | None = None,
) -> dict:
    hod = await get_current_hod(db, dept.id)
    coordinator = await get_current_coordinator(db, dept.id)
    hod_status = _mentor_status(hod)
    coord_status = _mentor_status(coordinator)
    invited_at, activated_at = _slot_timestamps(hod, hod_status)
    coord_invited_at, coord_activated_at = _slot_timestamps(coordinator, coord_status)

    return {
        "id": dept.id,
        "organization_id": dept.organization_id,
        "name": dept.name,
        "code": dept.code,
        "status": dept.status,
        "created_at": dept.created_at,
        "hod_name": f"{hod.first_name} {hod.last_name}".strip() if hod else None,
        "hod_email": hod.email if hod else None,
        "hod_status": hod_status,
        "coordinator_name": (
            f"{coordinator.first_name} {coordinator.last_name}".strip() if coordinator else None
        ),
        "coordinator_email": coordinator.email if coordinator else None,
        "coordinator_status": coord_status,
        "coordinator_invited_at": coord_invited_at,
        "coordinator_activated_at": coord_activated_at if coord_status == "active" else None,
        "student_count": await student_count(db, dept.id),
        "invited_at": invited_at,
        "activated_at": activated_at if hod_status == "active" else None,
        "mentor_history": await load_mentor_history(db, dept),
        "activation_token": activation_token,
        "activation_url": activation_url,
        "emailed": emailed,
        "message": message,
    }


def _lifecycle_from_enrich(payload: dict) -> dict:
    """Build FE lifecycle envelope. Never omit token/url when invite issued."""
    dept = {
        k: v
        for k, v in payload.items()
        if k
        not in {
            "activation_token",
            "activation_url",
            "emailed",
            "message",
        }
    }
    emailed = bool(payload.get("emailed"))
    token = payload.get("activation_token")
    url = payload.get("activation_url")
    portal_slug = payload.get("portal_slug")
    if token and not url:
        url = build_hod_activation_url(str(token), portal_slug=portal_slug)
    return {
        "message": payload.get("message") or "",
        "emailed": emailed,
        "activation_token": token,
        "activation_url": url,
        "department": dept,
    }


def _require_invite_delivery(
    raw_token: str | None,
    *,
    emailed: bool,
    portal_slug: str | None = None,
) -> tuple[str, str]:
    if not raw_token:
        raise DepartmentError(
            "Invite created but activation token missing. Retry or contact support.",
            status_code=500,
            code="HOD_INVITE_TOKEN_MISSING",
        )
    url = build_hod_activation_url(raw_token, portal_slug=portal_slug)
    return raw_token, url


async def _assert_dept_in_org(db: AsyncSession, department_id: int, actor: User):
    dept = await dept_service.get_department(db, department_id)
    if dept.organization_id != actor.organization_id:
        raise DepartmentError(
            "Department not in your organization.",
            status_code=403,
            code="DEPARTMENT_ORG_MISMATCH",
        )
    return dept


async def invite_mentor(
    db: AsyncSession,
    *,
    department_id: int,
    name: str,
    email: str,
    actor: User,
    title: str,
    activation_hours: int = 72,
) -> tuple[dict, str | None]:
    title = _normalize_title(title)
    label = _title_label(title)
    prefix = _audit_prefix(title)
    dept = await _assert_dept_in_org(db, department_id, actor)

    current = await get_mentor_by_title(db, department_id, title)
    if current is not None and current.status in _LIVE:
        raise DepartmentError(
            f"Department already has a {label}. Use reinvite or replace.",
            status_code=409,
            code=(
                "COORDINATOR_ALREADY_ASSIGNED"
                if title == _TITLE_COORD
                else "HOD_ALREADY_ASSIGNED"
            ),
        )

    email_norm = email.lower().strip()
    first_name, last_name = _split_name(name)
    role_id = await _dept_admin_role_id(db)

    # Same email cannot hold the other live mentor slot on this department.
    other_title = _TITLE_HOD if title == _TITLE_COORD else _TITLE_COORD
    other = await get_mentor_by_title(db, department_id, other_title)
    if (
        other is not None
        and other.status in _LIVE
        and other.email.lower() == email_norm
    ):
        other_label = _title_label(other_title)
        raise DepartmentError(
            f"Email is already the live {other_label} for this department.",
            status_code=409,
            code="MENTOR_EMAIL_SLOT_CONFLICT",
        )

    prior = await db.execute(
        select(User)
        .where(User.organization_id == actor.organization_id)
        .where(User.email == email_norm)
        .where(User.deleted_at.is_(None))
        .options(selectinload(User.organization), selectinload(User.role))
        .limit(1)
    )
    existing = prior.scalar_one_or_none()

    raw_token: str | None
    expires: datetime | None
    if existing is not None:
        if existing.role_id != role_id:
            raise DepartmentError(
                "Email already belongs to another user in this organization.",
                status_code=409,
                code="HOD_EMAIL_CONFLICT",
            )
        if (
            existing.department_id is not None
            and existing.department_id != dept.id
            and existing.status in _LIVE
        ):
            raise DepartmentError(
                "Email is already a department mentor of another department in this organization.",
                status_code=409,
                code="HOD_EMAIL_IN_USE",
            )
        # Live on this dept under the other title — already checked above via other slot.
        existing.department_id = dept.id
        existing.first_name = first_name
        existing.last_name = last_name
        existing.status = UserStatus.INVITED.value
        existing.password_hash = None
        existing.dept_admin_title = title
        raw_token = secrets.token_urlsafe(32)
        expires = datetime.now(timezone.utc) + timedelta(hours=activation_hours)
        existing.activation_token_hash = user_service._hash_token(raw_token)  # noqa: SLF001
        existing.activation_expires_at = expires
        await db.flush()
        user = await user_service.get_user(db, existing.id)
    else:
        username = _username_from_email(email_norm, dept.code)
        existing_u = await db.execute(
            select(User).where(
                User.organization_id == actor.organization_id,
                User.username == username,
                User.deleted_at.is_(None),
            )
        )
        if existing_u.scalar_one_or_none():
            username = f"{username}.{secrets.token_hex(2)}"

        user, raw_token, expires = await user_service.create_user(
            db,
            first_name=first_name,
            last_name=last_name,
            email=email_norm,
            username=username,
            password=None,
            role_code=RoleCode.DEPARTMENT_ADMIN.value,
            organization_id=actor.organization_id,
            department_id=dept.id,
            created_by=actor,
            activation_hours=activation_hours,
            dept_admin_title=title,
        )

    email_sent = False
    activation_url = None
    portal_slug = getattr(getattr(actor, "organization", None), "portal_slug", None) or getattr(
        getattr(user, "organization", None), "portal_slug", None
    )
    if raw_token and expires:
        activation_url = build_hod_activation_url(raw_token, portal_slug=portal_slug)
        email_sent = await user_service.send_hod_invite_email(
            user=user,
            raw_token=raw_token,
            expires=expires,
            role_label=_email_role_label(title),
        )

    raw_token, activation_url = _require_invite_delivery(
        raw_token, emailed=email_sent, portal_slug=portal_slug
    )

    await write_audit(
        db,
        organization_id=actor.organization_id,
        actor_user_id=actor.id,
        action=f"{prefix}.invite",
        entity_type="department",
        entity_id=dept.id,
        payload={
            "hod_user_id": user.id,
            "email": user.email,
            "name": f"{user.first_name} {user.last_name}".strip(),
            "email_sent": email_sent,
            "dept_admin_title": title,
        },
    )

    message = (
        f"{label} invited and activation email sent."
        if email_sent
        else f"{label} invited. Email not sent; share activation_token / activation_url manually."
    )
    enriched = await enrich_department(
        db,
        dept,
        activation_token=raw_token,
        activation_url=activation_url,
        emailed=email_sent,
        message=message,
    )
    return _lifecycle_from_enrich(enriched), raw_token


async def reinvite_mentor(
    db: AsyncSession,
    *,
    department_id: int,
    actor: User,
    title: str,
    activation_hours: int = 72,
) -> dict:
    title = _normalize_title(title)
    label = _title_label(title)
    prefix = _audit_prefix(title)
    dept = await _assert_dept_in_org(db, department_id, actor)

    mentor = await get_mentor_by_title(db, department_id, title)
    if mentor is None or mentor.status not in _LIVE:
        raise DepartmentError(
            f"No {label} to reinvite. Invite first.",
            status_code=404,
            code="COORDINATOR_NOT_FOUND" if title == _TITLE_COORD else "HOD_NOT_FOUND",
        )

    raw_token = secrets.token_urlsafe(32)
    expires = datetime.now(timezone.utc) + timedelta(hours=activation_hours)
    mentor.activation_token_hash = user_service._hash_token(raw_token)  # noqa: SLF001
    mentor.activation_expires_at = expires
    mentor.dept_admin_title = title
    if mentor.status == UserStatus.ACTIVE.value:
        mentor.status = UserStatus.INVITED.value
        mentor.password_hash = None
    await db.flush()
    mentor = await user_service.get_user(db, mentor.id)

    activation_url = build_hod_activation_url(
        raw_token,
        portal_slug=getattr(getattr(mentor, "organization", None), "portal_slug", None)
        or getattr(getattr(actor, "organization", None), "portal_slug", None),
    )
    email_sent = await user_service.send_hod_invite_email(
        user=mentor,
        raw_token=raw_token,
        expires=expires,
        role_label=_email_role_label(title),
    )
    portal_slug = getattr(getattr(mentor, "organization", None), "portal_slug", None) or getattr(
        getattr(actor, "organization", None), "portal_slug", None
    )
    raw_token, activation_url = _require_invite_delivery(
        raw_token, emailed=email_sent, portal_slug=portal_slug
    )

    await write_audit(
        db,
        organization_id=actor.organization_id,
        actor_user_id=actor.id,
        action=f"{prefix}.reinvite",
        entity_type="department",
        entity_id=dept.id,
        payload={
            "hod_user_id": mentor.id,
            "email": mentor.email,
            "name": f"{mentor.first_name} {mentor.last_name}".strip(),
            "email_sent": email_sent,
            "dept_admin_title": title,
        },
    )

    message = (
        f"{label} reinvited and activation email sent."
        if email_sent
        else f"{label} reinvited. Email not sent; share activation_token / activation_url manually."
    )
    enriched = await enrich_department(
        db,
        dept,
        activation_token=raw_token,
        activation_url=activation_url,
        emailed=email_sent,
        message=message,
    )
    return _lifecycle_from_enrich(enriched)


async def revoke_mentor(
    db: AsyncSession,
    *,
    department_id: int,
    actor: User,
    title: str,
    reason: str | None = None,
) -> dict:
    title = _normalize_title(title)
    label = _title_label(title)
    prefix = _audit_prefix(title)
    dept = await _assert_dept_in_org(db, department_id, actor)

    mentor = await get_mentor_by_title(db, department_id, title)
    if mentor is None or mentor.status not in _LIVE:
        raise DepartmentError(
            f"No active/invited {label} to revoke.",
            status_code=404,
            code="COORDINATOR_NOT_FOUND" if title == _TITLE_COORD else "HOD_NOT_FOUND",
        )

    mentor_name = f"{mentor.first_name} {mentor.last_name}".strip()
    mentor_email = mentor.email
    mentor.status = UserStatus.BLOCKED.value
    mentor.activation_token_hash = None
    mentor.activation_expires_at = None
    mentor.password_hash = None
    await db.flush()

    await write_audit(
        db,
        organization_id=actor.organization_id,
        actor_user_id=actor.id,
        action=f"{prefix}.revoke",
        entity_type="department",
        entity_id=dept.id,
        payload={
            "hod_user_id": mentor.id,
            "email": mentor_email,
            "name": mentor_name,
            "reason": reason or "",
            "dept_admin_title": title,
        },
    )

    enriched = await enrich_department(
        db,
        dept,
        emailed=False,
        message=f"{label} access revoked. Students remain in the department.",
    )
    return _lifecycle_from_enrich(enriched)


async def replace_mentor(
    db: AsyncSession,
    *,
    department_id: int,
    name: str,
    email: str,
    actor: User,
    title: str,
    reason: str | None = None,
    activation_hours: int = 72,
) -> dict:
    title = _normalize_title(title)
    label = _title_label(title)
    prefix = _audit_prefix(title)
    dept = await _assert_dept_in_org(db, department_id, actor)

    current = await get_mentor_by_title(db, department_id, title)
    previous_email = None
    if current is not None and current.status in _LIVE:
        previous_email = current.email
        current.status = UserStatus.BLOCKED.value
        current.activation_token_hash = None
        current.activation_expires_at = None
        current.password_hash = None
        await db.flush()

    lifecycle, _ = await invite_mentor(
        db,
        department_id=department_id,
        name=name,
        email=email,
        actor=actor,
        title=title,
        activation_hours=activation_hours,
    )

    await write_audit(
        db,
        organization_id=actor.organization_id,
        actor_user_id=actor.id,
        action=f"{prefix}.replace",
        entity_type="department",
        entity_id=dept.id,
        payload={
            "previous_hod_user_id": current.id if current else None,
            "reason": reason or "",
            "email": email.lower().strip(),
            "name": name.strip(),
            "new_email": email.lower().strip(),
            "replaced_by_email": email.lower().strip(),
            "previous_email": previous_email or "",
            "dept_admin_title": title,
        },
    )

    lifecycle["message"] = lifecycle.get("message") or f"{label} replaced. New invite sent."
    if reason:
        lifecycle["message"] = f"{lifecycle['message']} Reason: {reason}"
    return lifecycle


# ── Public HOD wrappers (unchanged API) ──────────────────────────────────────


async def invite_hod(
    db: AsyncSession,
    *,
    department_id: int,
    name: str,
    email: str,
    actor: User,
    activation_hours: int = 72,
) -> tuple[dict, str | None]:
    return await invite_mentor(
        db,
        department_id=department_id,
        name=name,
        email=email,
        actor=actor,
        title=_TITLE_HOD,
        activation_hours=activation_hours,
    )


async def reinvite_hod(
    db: AsyncSession,
    *,
    department_id: int,
    actor: User,
    activation_hours: int = 72,
) -> dict:
    return await reinvite_mentor(
        db,
        department_id=department_id,
        actor=actor,
        title=_TITLE_HOD,
        activation_hours=activation_hours,
    )


async def revoke_hod(
    db: AsyncSession,
    *,
    department_id: int,
    actor: User,
    reason: str | None = None,
) -> dict:
    return await revoke_mentor(
        db,
        department_id=department_id,
        actor=actor,
        title=_TITLE_HOD,
        reason=reason,
    )


async def replace_hod(
    db: AsyncSession,
    *,
    department_id: int,
    name: str,
    email: str,
    actor: User,
    reason: str | None = None,
    activation_hours: int = 72,
) -> dict:
    return await replace_mentor(
        db,
        department_id=department_id,
        name=name,
        email=email,
        actor=actor,
        title=_TITLE_HOD,
        reason=reason,
        activation_hours=activation_hours,
    )


# ── Placement Coordinator wrappers ───────────────────────────────────────────


async def invite_coordinator(
    db: AsyncSession,
    *,
    department_id: int,
    name: str,
    email: str,
    actor: User,
    activation_hours: int = 72,
) -> tuple[dict, str | None]:
    return await invite_mentor(
        db,
        department_id=department_id,
        name=name,
        email=email,
        actor=actor,
        title=_TITLE_COORD,
        activation_hours=activation_hours,
    )


async def reinvite_coordinator(
    db: AsyncSession,
    *,
    department_id: int,
    actor: User,
    activation_hours: int = 72,
) -> dict:
    return await reinvite_mentor(
        db,
        department_id=department_id,
        actor=actor,
        title=_TITLE_COORD,
        activation_hours=activation_hours,
    )


async def revoke_coordinator(
    db: AsyncSession,
    *,
    department_id: int,
    actor: User,
    reason: str | None = None,
) -> dict:
    return await revoke_mentor(
        db,
        department_id=department_id,
        actor=actor,
        title=_TITLE_COORD,
        reason=reason,
    )


async def replace_coordinator(
    db: AsyncSession,
    *,
    department_id: int,
    name: str,
    email: str,
    actor: User,
    reason: str | None = None,
    activation_hours: int = 72,
) -> dict:
    return await replace_mentor(
        db,
        department_id=department_id,
        name=name,
        email=email,
        actor=actor,
        title=_TITLE_COORD,
        reason=reason,
        activation_hours=activation_hours,
    )

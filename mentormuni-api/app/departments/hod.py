"""HOD invite / reinvite / revoke / replace for a department."""

from __future__ import annotations

import re
import secrets
from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.common.audit import write_audit
from app.common.email.templates import build_hod_activation_url
from app.departments import service as dept_service
from app.departments.service import DepartmentError
from app.models.audit_log import AuditLog
from app.models.enums import RoleCode, UserStatus
from app.models.role import Role
from app.models.user import User
from app.users import service as user_service

_HOD_AUDIT_ACTIONS = (
    "hod.invite",
    "hod.reinvite",
    "hod.revoke",
    "hod.replace",
    "hod.activate",
)

_EVENT_MAP = {
    "hod.invite": "invited",
    "hod.reinvite": "reinvited",
    "hod.revoke": "revoked",
    "hod.replace": "replaced",
    "hod.activate": "activated",
}


def _split_name(name: str) -> tuple[str, str]:
    parts = [p for p in re.split(r"\s+", name.strip()) if p]
    if not parts:
        return "HOD", "User"
    if len(parts) == 1:
        return parts[0], "User"
    return parts[0], " ".join(parts[1:])


def _username_from_email(email: str, department_code: str) -> str:
    local = email.split("@", 1)[0].lower()
    local = re.sub(r"[^a-z0-9._-]+", "", local) or "hod"
    code = re.sub(r"[^a-z0-9]+", "", department_code.lower()) or "dept"
    base = f"{local}.{code}"[:100]
    return base


def _hod_status(user: User | None) -> str:
    if user is None:
        return "unassigned"
    if user.status == UserStatus.INVITED.value:
        return "invited"
    if user.status == UserStatus.ACTIVE.value:
        return "active"
    if user.status == UserStatus.BLOCKED.value:
        return "revoked"
    return "unassigned"


async def get_current_hod(db: AsyncSession, department_id: int) -> User | None:
    """Prefer live HOD (INVITED/ACTIVE); else most recent BLOCKED (revoked) for display."""
    role_id = (
        await db.execute(select(Role.id).where(Role.role_code == RoleCode.DEPARTMENT_ADMIN.value))
    ).scalar_one()

    live = await db.execute(
        select(User)
        .where(User.department_id == department_id)
        .where(User.role_id == role_id)
        .where(User.deleted_at.is_(None))
        .where(User.status.in_([UserStatus.INVITED.value, UserStatus.ACTIVE.value]))
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
        .options(selectinload(User.organization), selectinload(User.role))
        .order_by(User.updated_at.desc())
        .limit(1)
    )
    return revoked.scalar_one_or_none()


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
                "event": _EVENT_MAP.get(row.action, row.action.replace("hod.", "")),
                "name": str(payload.get("name") or ""),
                "email": str(payload.get("email") or payload.get("new_email") or ""),
                "reason": str(payload.get("reason") or ""),
                "replaced_by_email": str(payload.get("replaced_by_email") or ""),
            }
        )
    return items


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
    status = _hod_status(hod)
    invited_at = None
    activated_at = None
    if hod is not None:
        if status == "invited":
            invited_at = hod.created_at
        elif status == "active":
            activated_at = hod.updated_at or hod.created_at
            invited_at = hod.created_at
        elif status == "revoked":
            invited_at = hod.created_at

    return {
        "id": dept.id,
        "organization_id": dept.organization_id,
        "name": dept.name,
        "code": dept.code,
        "status": dept.status,
        "created_at": dept.created_at,
        "hod_name": f"{hod.first_name} {hod.last_name}".strip() if hod else None,
        "hod_email": hod.email if hod else None,
        "hod_status": status,
        "student_count": await student_count(db, dept.id),
        "invited_at": invited_at,
        "activated_at": activated_at if status == "active" else None,
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
    # Contract: SMTP off / fail → emailed false BUT token+url always present for invite flows.
    if token and not url:
        url = build_hod_activation_url(str(token))
    return {
        "message": payload.get("message") or "",
        "emailed": emailed,
        "activation_token": token,
        "activation_url": url,
        "department": dept,
    }


def _require_invite_delivery(raw_token: str | None, *, emailed: bool) -> tuple[str, str]:
    """Invite must always expose token+url so FE never gets silent success."""
    if not raw_token:
        raise DepartmentError(
            "Invite created but activation token missing. Retry or contact support.",
            status_code=500,
            code="HOD_INVITE_TOKEN_MISSING",
        )
    url = build_hod_activation_url(raw_token)
    if not emailed:
        # Explicit ops path — FE shows manual copy.
        pass
    return raw_token, url


async def invite_hod(
    db: AsyncSession,
    *,
    department_id: int,
    name: str,
    email: str,
    actor: User,
    activation_hours: int = 72,
) -> tuple[dict, str | None]:
    dept = await dept_service.get_department(db, department_id)
    if dept.organization_id != actor.organization_id:
        raise DepartmentError(
            "Department not in your organization.",
            status_code=403,
            code="DEPARTMENT_ORG_MISMATCH",
        )

    current = await get_current_hod(db, department_id)
    if current is not None and current.status in {
        UserStatus.INVITED.value,
        UserStatus.ACTIVE.value,
    }:
        raise DepartmentError(
            "Department already has a HOD. Use reinvite or replace.",
            status_code=409,
            code="HOD_ALREADY_ASSIGNED",
        )

    email_norm = email.lower().strip()
    first_name, last_name = _split_name(name)
    role_id = (
        await db.execute(select(Role.id).where(Role.role_code == RoleCode.DEPARTMENT_ADMIN.value))
    ).scalar_one()

    # Revive blocked/deleted-email holder in this org (unique email constraint).
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
            and existing.status in {UserStatus.INVITED.value, UserStatus.ACTIVE.value}
        ):
            raise DepartmentError(
                "Email is already HOD of another department in this organization.",
                status_code=409,
                code="HOD_EMAIL_IN_USE",
            )
        existing.department_id = dept.id
        existing.first_name = first_name
        existing.last_name = last_name
        existing.status = UserStatus.INVITED.value
        existing.password_hash = None
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
        )

    email_sent = False
    activation_url = None
    if raw_token and expires:
        activation_url = build_hod_activation_url(raw_token)
        email_sent = await user_service.send_hod_invite_email(
            user=user, raw_token=raw_token, expires=expires
        )

    raw_token, activation_url = _require_invite_delivery(raw_token, emailed=email_sent)

    await write_audit(
        db,
        organization_id=actor.organization_id,
        actor_user_id=actor.id,
        action="hod.invite",
        entity_type="department",
        entity_id=dept.id,
        payload={
            "hod_user_id": user.id,
            "email": user.email,
            "name": f"{user.first_name} {user.last_name}".strip(),
            "email_sent": email_sent,
        },
    )

    message = (
        "HOD invited and activation email sent."
        if email_sent
        else "HOD invited. Email not sent; share activation_token / activation_url manually."
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


async def reinvite_hod(
    db: AsyncSession,
    *,
    department_id: int,
    actor: User,
    activation_hours: int = 72,
) -> dict:
    dept = await dept_service.get_department(db, department_id)
    if dept.organization_id != actor.organization_id:
        raise DepartmentError(
            "Department not in your organization.",
            status_code=403,
            code="DEPARTMENT_ORG_MISMATCH",
        )

    hod = await get_current_hod(db, department_id)
    if hod is None or hod.status not in {
        UserStatus.INVITED.value,
        UserStatus.ACTIVE.value,
    }:
        raise DepartmentError(
            "No HOD to reinvite. Invite first.",
            status_code=404,
            code="HOD_NOT_FOUND",
        )

    raw_token = secrets.token_urlsafe(32)
    expires = datetime.now(timezone.utc) + timedelta(hours=activation_hours)
    hod.activation_token_hash = user_service._hash_token(raw_token)  # noqa: SLF001
    hod.activation_expires_at = expires
    if hod.status == UserStatus.ACTIVE.value:
        # Force re-activation path (lost credentials / new device handoff)
        hod.status = UserStatus.INVITED.value
        hod.password_hash = None
    await db.flush()
    hod = await user_service.get_user(db, hod.id)

    activation_url = build_hod_activation_url(raw_token)
    email_sent = await user_service.send_hod_invite_email(
        user=hod, raw_token=raw_token, expires=expires
    )
    raw_token, activation_url = _require_invite_delivery(raw_token, emailed=email_sent)

    await write_audit(
        db,
        organization_id=actor.organization_id,
        actor_user_id=actor.id,
        action="hod.reinvite",
        entity_type="department",
        entity_id=dept.id,
        payload={
            "hod_user_id": hod.id,
            "email": hod.email,
            "name": f"{hod.first_name} {hod.last_name}".strip(),
            "email_sent": email_sent,
        },
    )

    message = (
        "HOD reinvited and activation email sent."
        if email_sent
        else "HOD reinvited. Email not sent; share activation_token / activation_url manually."
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


async def revoke_hod(
    db: AsyncSession,
    *,
    department_id: int,
    actor: User,
    reason: str | None = None,
) -> dict:
    dept = await dept_service.get_department(db, department_id)
    if dept.organization_id != actor.organization_id:
        raise DepartmentError(
            "Department not in your organization.",
            status_code=403,
            code="DEPARTMENT_ORG_MISMATCH",
        )

    hod = await get_current_hod(db, department_id)
    if hod is None or hod.status not in {
        UserStatus.INVITED.value,
        UserStatus.ACTIVE.value,
    }:
        raise DepartmentError(
            "No active/invited HOD to revoke.",
            status_code=404,
            code="HOD_NOT_FOUND",
        )

    hod_name = f"{hod.first_name} {hod.last_name}".strip()
    hod_email = hod.email
    hod.status = UserStatus.BLOCKED.value
    hod.activation_token_hash = None
    hod.activation_expires_at = None
    hod.password_hash = None
    await db.flush()

    await write_audit(
        db,
        organization_id=actor.organization_id,
        actor_user_id=actor.id,
        action="hod.revoke",
        entity_type="department",
        entity_id=dept.id,
        payload={
            "hod_user_id": hod.id,
            "email": hod_email,
            "name": hod_name,
            "reason": reason or "",
        },
    )

    enriched = await enrich_department(
        db,
        dept,
        emailed=False,
        message="HOD access revoked. Students remain in the department.",
    )
    return _lifecycle_from_enrich(enriched)


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
    dept = await dept_service.get_department(db, department_id)
    if dept.organization_id != actor.organization_id:
        raise DepartmentError(
            "Department not in your organization.",
            status_code=403,
            code="DEPARTMENT_ORG_MISMATCH",
        )

    current = await get_current_hod(db, department_id)
    previous_email = None
    if current is not None and current.status in {
        UserStatus.INVITED.value,
        UserStatus.ACTIVE.value,
    }:
        previous_email = current.email
        current.status = UserStatus.BLOCKED.value
        current.activation_token_hash = None
        current.activation_expires_at = None
        current.password_hash = None
        await db.flush()

    # Invite new — reuse invite path but current is now revoked so no 409
    lifecycle, _ = await invite_hod(
        db,
        department_id=department_id,
        name=name,
        email=email,
        actor=actor,
        activation_hours=activation_hours,
    )

    await write_audit(
        db,
        organization_id=actor.organization_id,
        actor_user_id=actor.id,
        action="hod.replace",
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
        },
    )

    lifecycle["message"] = (
        lifecycle.get("message") or "HOD replaced. New invite sent."
    )
    if reason:
        lifecycle["message"] = f"{lifecycle['message']} Reason: {reason}"
    return lifecycle

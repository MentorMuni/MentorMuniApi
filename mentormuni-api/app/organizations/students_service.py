"""Org Portal student enrollment — invite / import / roster / approve."""

from __future__ import annotations

import csv
import io
import re
import secrets
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.common.audit import write_audit
from app.common.tenant.context import TenantContext
from app.models.enums import RoleCode, UserStatus
from app.models.user import User
from app.users import service as user_service


class StudentPortalError(Exception):
    def __init__(self, message: str, *, status_code: int = 400) -> None:
        super().__init__(message)
        self.message = message
        self.status_code = status_code


def _split_name(name: str | None, email: str) -> tuple[str, str]:
    raw = (name or "").strip()
    if not raw:
        local = email.split("@", 1)[0]
        raw = local.replace(".", " ").replace("_", " ").replace("-", " ")
    parts = [p for p in re.split(r"\s+", raw) if p]
    if not parts:
        return "Student", "User"
    if len(parts) == 1:
        return parts[0][:128], "User"
    return parts[0][:128], " ".join(parts[1:])[:128]


def _username_from_email(email: str) -> str:
    local = email.split("@", 1)[0].lower()
    local = re.sub(r"[^a-z0-9._-]+", "", local) or "student"
    return local[:100]


def _auth_status(user: User) -> str:
    if user.status == UserStatus.INVITED.value or not user.password_hash:
        if user.status in {UserStatus.INVITED.value, UserStatus.PENDING.value}:
            return "needs_password"
        if user.status == UserStatus.ACTIVE.value and user.password_hash:
            return "ready"
        return "needs_password"
    return "ready"


def _invite_status(user: User) -> str:
    if user.status == UserStatus.PENDING.value:
        return "pending"
    if user.status == UserStatus.REJECTED.value:
        return "rejected"
    if user.status in {UserStatus.ACTIVE.value, UserStatus.INVITED.value}:
        return "approved"
    return user.status.lower()


def to_invite_row(user: User, *, source: str | None = None) -> dict:
    return {
        "id": user.id,
        "email": user.email,
        "name": f"{user.first_name} {user.last_name}".strip(),
        "department_id": user.department_id,
        "department_name": user.department.name if user.department else None,
        "roll_number": user.roll_number,
        "batch_year": user.batch_year,
        "phone": user.mobile,
        "mobile": user.mobile,
        "status": _invite_status(user),
        "source": source,
        "created_at": user.created_at,
    }


def to_student_row(
    user: User,
    *,
    source: str | None = None,
    setup_url: str | None = None,
    activation_token: str | None = None,
    message: str | None = None,
) -> dict:
    return {
        "id": user.id,
        "email": user.email,
        "name": f"{user.first_name} {user.last_name}".strip(),
        "first_name": user.first_name,
        "last_name": user.last_name,
        "username": user.username,
        "organization_id": user.organization_id,
        "department_id": user.department_id,
        "department_name": user.department.name if user.department else None,
        "department_code": user.department.code if user.department else None,
        "roll_number": user.roll_number,
        "batch_year": user.batch_year,
        "status": user.status.lower() if user.status else user.status,
        "auth_status": _auth_status(user),
        "source": source,
        "created_at": user.created_at,
        "approved_at": user.approved_at,
        "setup_url": setup_url,
        "activation_token": activation_token,
        "message": message,
    }


def _resolve_department_id(ctx: TenantContext, department_id: int | None) -> int:
    if ctx.role == RoleCode.DEPARTMENT_ADMIN.value:
        if ctx.department_id is None:
            raise StudentPortalError("HOD has no department assigned.", status_code=400)
        if department_id is not None and department_id != ctx.department_id:
            raise StudentPortalError(
                "HOD can only manage students in their own department.",
                status_code=403,
            )
        return ctx.department_id
    if department_id is None:
        raise StudentPortalError("department_id is required.", status_code=422)
    return department_id


async def list_roster(
    db: AsyncSession,
    ctx: TenantContext,
    *,
    department_id: int | None = None,
) -> tuple[list[dict], int]:
    dept = department_id
    if not ctx.sees_all_students:
        dept = ctx.department_id

    items, total = await user_service.list_users(
        db,
        organization_id=ctx.organization_id,
        department_id=dept,
        role_code=RoleCode.STUDENT.value,
    )
    # Roster = enrolled (ACTIVE or INVITED awaiting password). Exclude PENDING queue + REJECTED.
    roster = [
        to_student_row(u)
        for u in items
        if u.status in {UserStatus.ACTIVE.value, UserStatus.INVITED.value, UserStatus.BLOCKED.value}
    ]
    return roster, len(roster)


async def list_invites(
    db: AsyncSession,
    ctx: TenantContext,
    *,
    status: str | None = "pending",
    department_id: int | None = None,
) -> tuple[list[dict], int]:
    dept = department_id
    if not ctx.sees_all_students:
        dept = ctx.department_id

    status_filter = None
    if status:
        s = status.strip().lower()
        if s == "pending":
            status_filter = UserStatus.PENDING.value
        elif s == "rejected":
            status_filter = UserStatus.REJECTED.value
        elif s == "approved":
            # approved queue already moved to roster — return INVITED+ACTIVE if asked
            status_filter = None
        else:
            status_filter = status.upper()

    items, _ = await user_service.list_users(
        db,
        organization_id=ctx.organization_id,
        department_id=dept,
        status=status_filter,
        role_code=RoleCode.STUDENT.value,
    )
    if status and status.strip().lower() == "approved":
        items = [
            u
            for u in items
            if u.status in {UserStatus.ACTIVE.value, UserStatus.INVITED.value}
        ]
    elif status is None or status.strip().lower() == "pending":
        items = [u for u in items if u.status == UserStatus.PENDING.value]

    rows = [to_invite_row(u) for u in items]
    return rows, len(rows)


async def invite_emails(
    db: AsyncSession,
    ctx: TenantContext,
    *,
    emails: list[str],
    department_id: int,
    source: str = "invite",
) -> tuple[int, int, list[str], list[dict]]:
    dept_id = _resolve_department_id(ctx, department_id)
    created_rows: list[dict] = []
    skipped = 0
    errors: list[str] = []

    for email in emails:
        email_norm = str(email).lower().strip()
        first_name, last_name = _split_name(None, email_norm)
        username = _username_from_email(email_norm)
        # uniquify username on collision
        try:
            user, _, _ = await user_service.create_user(
                db,
                first_name=first_name,
                last_name=last_name,
                email=email_norm,
                username=username,
                password=None,
                role_code=RoleCode.STUDENT.value,
                organization_id=ctx.organization_id,
                department_id=dept_id,
                created_by=ctx.user,
                invite_without_password=True,
            )
            created_rows.append(to_invite_row(user, source=source))
        except user_service.UserServiceError as exc:
            if exc.status_code == 409:
                # retry with unique username if only username collided
                try:
                    user, _, _ = await user_service.create_user(
                        db,
                        first_name=first_name,
                        last_name=last_name,
                        email=email_norm,
                        username=f"{username}.{secrets.token_hex(2)}",
                        password=None,
                        role_code=RoleCode.STUDENT.value,
                        organization_id=ctx.organization_id,
                        department_id=dept_id,
                        created_by=ctx.user,
                        invite_without_password=True,
                    )
                    created_rows.append(to_invite_row(user, source=source))
                    continue
                except user_service.UserServiceError as exc2:
                    if exc2.status_code == 409:
                        skipped += 1
                        errors.append(f"{email_norm}: already exists")
                    else:
                        errors.append(f"{email_norm}: {exc2.message}")
            else:
                errors.append(f"{email_norm}: {exc.message}")

    await write_audit(
        db,
        organization_id=ctx.organization_id,
        actor_user_id=ctx.user_id,
        action="student.invite",
        entity_type="department",
        entity_id=dept_id,
        payload={"created": len(created_rows), "skipped": skipped, "source": source},
    )
    return len(created_rows), skipped, errors, created_rows


async def create_manual(
    db: AsyncSession,
    ctx: TenantContext,
    *,
    name: str,
    email: str,
    department_id: int,
    roll_number: str | None = None,
    batch_year: int | None = None,
    source: str = "manual",
) -> dict:
    dept_id = _resolve_department_id(ctx, department_id)
    email_norm = email.lower().strip()
    first_name, last_name = _split_name(name, email_norm)
    username = _username_from_email(email_norm)
    try:
        user, _, _ = await user_service.create_user(
            db,
            first_name=first_name,
            last_name=last_name,
            email=email_norm,
            username=username,
            password=None,
            role_code=RoleCode.STUDENT.value,
            organization_id=ctx.organization_id,
            department_id=dept_id,
            created_by=ctx.user,
            invite_without_password=True,
            roll_number=roll_number,
            batch_year=batch_year,
        )
    except user_service.UserServiceError as exc:
        if exc.status_code == 409:
            user, _, _ = await user_service.create_user(
                db,
                first_name=first_name,
                last_name=last_name,
                email=email_norm,
                username=f"{username}.{secrets.token_hex(2)}",
                password=None,
                role_code=RoleCode.STUDENT.value,
                organization_id=ctx.organization_id,
                department_id=dept_id,
                created_by=ctx.user,
                invite_without_password=True,
                roll_number=roll_number,
                batch_year=batch_year,
            )
        else:
            raise StudentPortalError(exc.message, status_code=exc.status_code) from exc

    await write_audit(
        db,
        organization_id=ctx.organization_id,
        actor_user_id=ctx.user_id,
        action="student.invite",
        entity_type="user",
        entity_id=user.id,
        payload={"source": source},
    )
    return to_invite_row(user, source=source)


def _parse_csv_rows(csv_text: str) -> list[dict]:
    reader = csv.DictReader(io.StringIO(csv_text))
    if not reader.fieldnames:
        raise StudentPortalError("CSV is empty or missing headers.", status_code=422)
    field_map = {h.strip().lower(): h for h in reader.fieldnames}
    rows: list[dict] = []
    for i, row in enumerate(reader, start=2):
        def cell(*keys: str) -> str:
            for k in keys:
                raw = field_map.get(k)
                if raw and row.get(raw):
                    return str(row.get(raw) or "").strip()
            return ""

        email = cell("email")
        if not email:
            continue
        name = cell("name", "full_name")
        if not name:
            fn = cell("first_name")
            ln = cell("last_name")
            name = f"{fn} {ln}".strip()
        batch_raw = cell("batch_year", "batch", "year")
        batch_year = int(batch_raw) if batch_raw.isdigit() else None
        rows.append(
            {
                "email": email,
                "name": name or None,
                "roll_number": cell("roll_number", "roll", "roll_no", "college_id") or None,
                "batch_year": batch_year,
                "row": i,
            }
        )
    return rows


async def import_students(
    db: AsyncSession,
    ctx: TenantContext,
    *,
    department_id: int,
    rows: list[dict] | None = None,
    csv_text: str | None = None,
    send_invite_email: bool = False,
    source: str = "import",
) -> tuple[int, int, int, list[dict], list[dict]]:
    dept_id = _resolve_department_id(ctx, department_id)
    parsed = list(rows or [])
    if csv_text:
        parsed.extend(_parse_csv_rows(csv_text))
    if not parsed:
        raise StudentPortalError("No rows to import.", status_code=422)

    created = 0
    updated = 0
    skipped = 0
    errors: list[dict] = []
    items: list[dict] = []

    for idx, row in enumerate(parsed):
        email = str(row.get("email") or "").lower().strip()
        row_num = row.get("row", idx + 1)
        if not email or "@" not in email:
            errors.append({"row": row_num, "email": email, "message": "Invalid email"})
            continue
        first_name, last_name = _split_name(row.get("name"), email)
        username = _username_from_email(email)
        roll = row.get("roll_number")
        batch = row.get("batch_year")
        try:
            user, _, _ = await user_service.create_user(
                db,
                first_name=first_name,
                last_name=last_name,
                email=email,
                username=username,
                password=None,
                role_code=RoleCode.STUDENT.value,
                organization_id=ctx.organization_id,
                department_id=dept_id,
                created_by=ctx.user,
                invite_without_password=True,
                roll_number=str(roll) if roll else None,
                batch_year=int(batch) if batch is not None else None,
            )
        except user_service.UserServiceError as exc:
            if exc.status_code == 409:
                try:
                    user, _, _ = await user_service.create_user(
                        db,
                        first_name=first_name,
                        last_name=last_name,
                        email=email,
                        username=f"{username}.{secrets.token_hex(2)}",
                        password=None,
                        role_code=RoleCode.STUDENT.value,
                        organization_id=ctx.organization_id,
                        department_id=dept_id,
                        created_by=ctx.user,
                        invite_without_password=True,
                        roll_number=str(roll) if roll else None,
                        batch_year=int(batch) if batch is not None else None,
                    )
                except user_service.UserServiceError as exc2:
                    skipped += 1
                    errors.append({"row": row_num, "email": email, "message": exc2.message})
                    continue
            else:
                errors.append({"row": row_num, "email": email, "message": exc.message})
                continue

        created += 1
        if send_invite_email:
            try:
                user, token, setup_url, email_sent = await user_service.approve_user(
                    db, user_id=user.id, approver=ctx.user, send_password_email=True
                )
                items.append(
                    to_student_row(
                        user,
                        source=source,
                        setup_url=setup_url,
                        activation_token=token,
                    )
                )
            except user_service.UserServiceError as exc:
                errors.append({"row": row_num, "email": email, "message": exc.message})
                items.append(to_invite_row(user, source=source))
        else:
            items.append(to_invite_row(user, source=source))

    await write_audit(
        db,
        organization_id=ctx.organization_id,
        actor_user_id=ctx.user_id,
        action="student.import",
        entity_type="department",
        entity_id=dept_id,
        payload={
            "created": created,
            "skipped": skipped,
            "errors": len(errors),
            "send_invite_email": send_invite_email,
        },
    )
    return created, updated, skipped, errors, items


async def approve_invite(
    db: AsyncSession,
    ctx: TenantContext,
    *,
    invite_id: int,
) -> dict:
    user = await user_service.get_user(db, invite_id)
    if user.organization_id != ctx.organization_id:
        raise StudentPortalError("Invite not in your organization.", status_code=403)
    if not ctx.sees_all_students and user.department_id != ctx.department_id:
        raise StudentPortalError("Outside your department.", status_code=403)

    try:
        user, token, setup_url, email_sent = await user_service.approve_user(
            db, user_id=invite_id, approver=ctx.user
        )
    except user_service.UserServiceError as exc:
        raise StudentPortalError(exc.message, status_code=exc.status_code) from exc

    message = (
        "Approved. Set-password email sent."
        if email_sent
        else (
            "Approved. Share the set-password link with the student."
            if setup_url
            else "Approved. Student can log in."
        )
    )
    return {
        "student": to_student_row(
            user,
            setup_url=setup_url,
            activation_token=token,
            message=message,
        ),
        "email_sent": email_sent,
        "activation_token": token,
        "setup_url": setup_url,
        "message": message,
    }


async def reject_invite(
    db: AsyncSession,
    ctx: TenantContext,
    *,
    invite_id: int,
) -> dict:
    user = await user_service.get_user(db, invite_id)
    if user.organization_id != ctx.organization_id:
        raise StudentPortalError("Invite not in your organization.", status_code=403)
    if not ctx.sees_all_students and user.department_id != ctx.department_id:
        raise StudentPortalError("Outside your department.", status_code=403)
    try:
        user = await user_service.reject_user(db, user_id=invite_id, approver=ctx.user)
    except user_service.UserServiceError as exc:
        raise StudentPortalError(exc.message, status_code=exc.status_code) from exc
    return to_invite_row(user)


async def resend_setup_link(
    db: AsyncSession,
    ctx: TenantContext,
    *,
    student_id: int,
) -> dict:
    """
    Regenerate set-password token + email.

    PENDING → same as approve (first-time setup email).
    INVITED / ACTIVE / BLOCKED student → rotate token and resend.
    """
    user = await user_service.get_user(db, student_id)
    if user.organization_id != ctx.organization_id:
        raise StudentPortalError("Student not in your organization.", status_code=403)
    if user.role.role_code != RoleCode.STUDENT.value:
        raise StudentPortalError("Not a student.", status_code=400)
    if not ctx.sees_all_students and user.department_id != ctx.department_id:
        raise StudentPortalError("Outside your department.", status_code=403)

    if user.status == UserStatus.PENDING.value:
        return await approve_invite(db, ctx, invite_id=student_id)

    if user.status == UserStatus.REJECTED.value:
        raise StudentPortalError(
            "Student was rejected. Re-invite or ask them to enroll again.",
            status_code=400,
        )

    try:
        user, token, setup_url, email_sent = await user_service.issue_student_activation(
            db, user=user, actor=ctx.user, send_email=True
        )
    except user_service.UserServiceError as exc:
        raise StudentPortalError(exc.message, status_code=exc.status_code) from exc

    message = (
        "Set-password email resent."
        if email_sent
        else "Set-password link ready. Share it with the student."
    )
    return {
        "student": to_student_row(
            user,
            setup_url=setup_url,
            activation_token=token,
            message=message,
        ),
        "email_sent": email_sent,
        "emailed": email_sent,
        "activation_token": token,
        "setup_url": setup_url,
        "message": message,
    }


async def patch_student(
    db: AsyncSession,
    ctx: TenantContext,
    *,
    student_id: int,
    fields: dict,
) -> dict:
    user = await user_service.get_user(db, student_id)
    if user.organization_id != ctx.organization_id:
        raise StudentPortalError("Student not in your organization.", status_code=403)
    if user.role.role_code != RoleCode.STUDENT.value:
        raise StudentPortalError("Not a student.", status_code=400)
    if not ctx.sees_all_students and user.department_id != ctx.department_id:
        raise StudentPortalError("Outside your department.", status_code=403)

    if "department_id" in fields and fields["department_id"] is not None:
        if ctx.role == RoleCode.DEPARTMENT_ADMIN.value:
            raise StudentPortalError("HOD cannot reassign department.", status_code=403)
        fields["department_id"] = int(fields["department_id"])

    if "status" in fields and fields["status"]:
        fields["status"] = str(fields["status"]).upper()

    try:
        user = await user_service.update_user(db, student_id, **fields)
    except user_service.UserServiceError as exc:
        raise StudentPortalError(exc.message, status_code=exc.status_code) from exc

    await write_audit(
        db,
        organization_id=ctx.organization_id,
        actor_user_id=ctx.user_id,
        action="student.update",
        entity_type="user",
        entity_id=user.id,
        payload=fields,
    )
    return to_student_row(user)

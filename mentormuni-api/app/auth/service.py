"""Auth service: login, me, change-password, forgot/reset password."""

from __future__ import annotations

import hashlib
import logging
import secrets
from datetime import datetime, timedelta, timezone

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.common.email.exceptions import EmailError
from app.common.email.flows import send_password_reset_email
from app.common.organization_access import (
    OrganizationAccessError,
    ensure_organization_active_for_login,
)
from app.common.security.passwords import hash_password, verify_password
from app.common.tenant.deps import build_tenant_context, load_permissions_for_role
from app.models.enums import RoleCode
from app.organizations.hod_access_service import (
    filter_permissions_for_hod,
    get_hod_access_policy,
)
from app.core.config import settings
from app.models.enums import DeptAdminTitle, RoleCode, UserStatus
from app.models.organization import Organization
from app.models.user import User

logger = logging.getLogger(__name__)

# FE-preferred role labels (DB still uses ORG_ADMIN / DEPARTMENT_ADMIN).
_FE_ROLE_ALIAS = {
    RoleCode.ORG_ADMIN.value: "TPO",
    RoleCode.DEPARTMENT_ADMIN.value: "HOD",
    RoleCode.STUDENT.value: "STUDENT",
}


class AuthError(Exception):
    def __init__(
        self,
        message: str,
        *,
        status_code: int = 400,
        code: str | None = None,
        extra: dict | None = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.code = code
        self.extra = dict(extra or {})


def fe_role_alias(role_code: str | None) -> str:
    if not role_code:
        return "VIEWER"
    return _FE_ROLE_ALIAS.get(role_code, role_code)


def dept_admin_title_for(user: User) -> str | None:
    role_code = user.role.role_code if user.role else None
    if role_code != RoleCode.DEPARTMENT_ADMIN.value:
        return None
    raw = (getattr(user, "dept_admin_title", None) or DeptAdminTitle.HOD.value).strip().upper()
    if raw == DeptAdminTitle.PLACEMENT_COORDINATOR.value:
        return DeptAdminTitle.PLACEMENT_COORDINATOR.value
    return DeptAdminTitle.HOD.value


def role_display_label(user: User, role_code: str | None = None) -> str:
    code = role_code or (user.role.role_code if user.role else None)
    if code == RoleCode.DEPARTMENT_ADMIN.value:
        title = dept_admin_title_for(user)
        if title == DeptAdminTitle.PLACEMENT_COORDINATOR.value:
            return "Placement Coordinator"
        return "HOD"
    return fe_role_alias(code)


def user_display_name(user: User) -> str:
    return f"{user.first_name} {user.last_name}".strip() or user.email


_ORG_PORTAL_KEYS = frozenset({"organization", "org", "orgportal"})
_STUDENT_PORTAL_KEYS = frozenset({"student", "students", "studentportal"})


def ensure_login_portal_allowed(
    user: User,
    *,
    portal: str | None,
    organization_code: str | None,
) -> None:
    """Reject cross-portal logins and org-portal access without matching college code."""
    if not portal or not str(portal).strip():
        raise AuthError(
            "Portal is required (organization or student).",
            status_code=422,
            code="PORTAL_REQUIRED",
        )

    portal_key = portal.strip().lower()
    role_code = user.role.role_code if user.role else None
    staff_roles = {RoleCode.ORG_ADMIN.value, RoleCode.DEPARTMENT_ADMIN.value}

    if portal_key in _ORG_PORTAL_KEYS:
        if role_code not in staff_roles:
            raise AuthError(
                "Student accounts must use the student portal (My Performance).",
                status_code=403,
                code="WRONG_PORTAL",
            )
        code = (organization_code or "").strip().upper()
        if not code:
            raise AuthError(
                "College code is required to sign in to the organization portal.",
                status_code=422,
                code="ORGANIZATION_CODE_REQUIRED",
            )
        if not user.organization or user.organization.code.upper() != code:
            raise AuthError(
                "These credentials do not match this college code.",
                status_code=403,
                code="WRONG_TENANT",
            )
        return

    if portal_key in _STUDENT_PORTAL_KEYS:
        if role_code in staff_roles:
            raise AuthError(
                "TPO and HOD accounts must use the organization portal.",
                status_code=403,
                code="WRONG_PORTAL",
            )
        if role_code != RoleCode.STUDENT.value:
            raise AuthError(
                "This portal is for student accounts only.",
                status_code=403,
                code="WRONG_PORTAL",
            )
        return

    raise AuthError(
        "Unknown portal. Use organization or student.",
        status_code=422,
        code="INVALID_PORTAL",
    )


def _hash_token(raw: str) -> str:
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


async def authenticate_user(
    db: AsyncSession,
    *,
    password: str,
    email: str | None = None,
    username: str | None = None,
    organization_code: str | None = None,
) -> User:
    if not email and not username:
        raise AuthError("Provide email or username.", status_code=422)

    stmt = (
        select(User)
        .join(Organization, User.organization_id == Organization.id)
        .where(User.deleted_at.is_(None))
        .options(
            selectinload(User.role),
            selectinload(User.organization),
            selectinload(User.department),
        )
    )

    if organization_code:
        stmt = stmt.where(Organization.code == organization_code.upper())

    if email and username:
        stmt = stmt.where(or_(User.email == email.lower(), User.username == username))
    elif email:
        stmt = stmt.where(User.email == email.lower())
    else:
        stmt = stmt.where(User.username == username)

    result = await db.execute(stmt)
    users = list(result.scalars().unique().all())

    if not users:
        if organization_code:
            await _raise_if_wrong_tenant(
                db,
                email=email,
                username=username,
                password=password,
                requested_code=organization_code.upper(),
            )
        raise AuthError(
            "Invalid credentials.",
            status_code=401,
            code="INVALID_CREDENTIALS",
        )
    if len(users) > 1:
        raise AuthError(
            "Multiple accounts match. Pass organization_code to disambiguate.",
            status_code=400,
        )

    user = users[0]
    if not user.password_hash or not verify_password(password, user.password_hash):
        raise AuthError(
            "Invalid credentials.",
            status_code=401,
            code="INVALID_CREDENTIALS",
        )

    # College host must never accept PUBLIC / individual accounts.
    if organization_code and user.organization:
        from app.common.portal_slug import apex_portal_base_url
        from app.models.enums import OrganizationType

        req = await db.execute(
            select(Organization).where(Organization.code == organization_code.upper())
        )
        requested_org = req.scalar_one_or_none()
        if (
            requested_org
            and str(requested_org.organization_type).upper() == OrganizationType.COLLEGE.value
            and str(user.organization.organization_type).upper() == OrganizationType.PUBLIC.value
        ):
            raise AuthError(
                "Individual accounts sign in at mentormuni.com, not a college portal.",
                status_code=403,
                code="PUBLIC_ON_COLLEGE",
                extra={"portal_url": apex_portal_base_url()},
            )

    if user.status == UserStatus.INVITED.value:
        raise AuthError(
            "Account invited but not activated. Set your password via the activation link.",
            status_code=403,
            code="ACCOUNT_INACTIVE",
        )
    if user.status == UserStatus.PENDING.value:
        raise AuthError(
            "Account pending approval.",
            status_code=403,
            code="ACCOUNT_INACTIVE",
        )
    if user.status == UserStatus.REJECTED.value:
        raise AuthError(
            "Account was rejected.",
            status_code=403,
            code="ACCOUNT_INACTIVE",
        )
    if user.status == UserStatus.BLOCKED.value:
        raise AuthError(
            "Account is blocked.",
            status_code=403,
            code="ACCOUNT_INACTIVE",
        )
    if user.status != UserStatus.ACTIVE.value:
        raise AuthError(
            f"Account is {user.status}.",
            status_code=403,
            code="ACCOUNT_INACTIVE",
        )

    try:
        role_code = user.role.role_code if user.role else None
        ensure_organization_active_for_login(user.organization, role_code=role_code)
    except OrganizationAccessError as exc:
        raise AuthError(
            exc.message,
            status_code=exc.status_code,
            code="ORG_SUSPENDED",
        ) from exc

    return user


async def _raise_if_wrong_tenant(
    db: AsyncSession,
    *,
    email: str | None,
    username: str | None,
    password: str,
    requested_code: str,
) -> None:
    """If password matches another org, raise WRONG_TENANT with correct portal URL."""
    from app.common.portal_slug import apex_portal_base_url, college_portal_base_url
    from app.models.enums import OrganizationType

    stmt = (
        select(User)
        .join(Organization, User.organization_id == Organization.id)
        .where(User.deleted_at.is_(None))
        .options(selectinload(User.organization), selectinload(User.role))
    )
    if email and username:
        stmt = stmt.where(or_(User.email == email.lower(), User.username == username))
    elif email:
        stmt = stmt.where(User.email == email.lower())
    else:
        stmt = stmt.where(User.username == username)

    candidates = list((await db.execute(stmt)).scalars().unique().all())
    matches = [
        u
        for u in candidates
        if u.password_hash and verify_password(password, u.password_hash)
    ]
    if not matches:
        return
    user = matches[0]
    home = user.organization
    if home is None or home.code.upper() == requested_code:
        return

    if str(home.organization_type).upper() == OrganizationType.PUBLIC.value:
        raise AuthError(
            "Individual accounts sign in at mentormuni.com, not a college portal.",
            status_code=403,
            code="PUBLIC_ON_COLLEGE",
            extra={"portal_url": apex_portal_base_url()},
        )

    portal = college_portal_base_url(home.portal_slug)
    raise AuthError(
        f"This account belongs to {home.name}. Open {portal} to sign in.",
        status_code=403,
        code="WRONG_TENANT",
        extra={
            "portal_url": portal,
            "organization_code": home.code,
            "organization_name": home.name,
            "portal_slug": home.portal_slug,
        },
    )


async def permissions_for_user(db: AsyncSession, user: User) -> list[str]:
    perms = await load_permissions_for_role(db, user.role_id)
    if (
        user.role
        and user.role.role_code == RoleCode.DEPARTMENT_ADMIN.value
        and user.organization_id is not None
    ):
        policy = await get_hod_access_policy(db, user.organization_id)
        perms = filter_permissions_for_hod(perms, policy)
    return sorted(perms)


async def change_password(
    db: AsyncSession,
    *,
    user: User,
    current_password: str,
    new_password: str,
) -> None:
    if not user.password_hash or not verify_password(current_password, user.password_hash):
        raise AuthError("Current password is incorrect.", status_code=400)
    user.password_hash = hash_password(new_password)
    user.must_change_password = False
    await db.flush()


async def request_password_reset(
    db: AsyncSession,
    *,
    email: str | None = None,
    username: str | None = None,
    identifier: str | None = None,
    organization_code: str | None = None,
    portal: str | None = "organization",
) -> tuple[str, bool, str | None]:
    """
    Always returns a generic success message to the caller.

    Lookup: email and/or username (or a single identifier = college ID / email).
    If a matching ACTIVE user with a password exists, emails a reset link.

    Returns (message, emailed, reset_url|None).
    reset_url is included when a token was minted but email did not send,
    so staff can still share the link.
    """
    from app.common.email.templates import build_password_reset_url

    generic = "If an account exists for those details, a reset link has been sent."

    email_norm = (email or "").strip().lower() or None
    username_norm = (username or "").strip() or None
    ident = (identifier or "").strip() or None
    if ident and not email_norm and not username_norm:
        if "@" in ident:
            email_norm = ident.lower()
        else:
            username_norm = ident

    if not email_norm and not username_norm:
        return generic, False, None

    portal_key = (portal or "organization").strip().lower()
    if portal_key in {"student", "students", "studentportal"}:
        reset_path = settings.student_password_reset_path or "/studentportal/reset-password"
    else:
        reset_path = settings.password_reset_path or "/Organization/reset-password"

    stmt = (
        select(User)
        .join(Organization, User.organization_id == Organization.id)
        .where(User.deleted_at.is_(None))
        .options(selectinload(User.organization), selectinload(User.role))
    )
    if organization_code:
        stmt = stmt.where(Organization.code == organization_code.upper().strip())

    if email_norm and username_norm:
        stmt = stmt.where(
            or_(User.email == email_norm, User.username == username_norm)
        )
    elif email_norm:
        stmt = stmt.where(User.email == email_norm)
    else:
        stmt = stmt.where(User.username == username_norm)

    result = await db.execute(stmt)
    users = list(result.scalars().unique().all())
    if len(users) != 1:
        return generic, False, None

    user = users[0]
    if user.status != UserStatus.ACTIVE.value or not user.password_hash:
        return generic, False, None

    raw_token = secrets.token_urlsafe(32)
    user.password_reset_token_hash = _hash_token(raw_token)
    user.password_reset_expires_at = datetime.now(timezone.utc) + timedelta(hours=2)
    await db.flush()

    reset_url = build_password_reset_url(
        raw_token,
        path=reset_path,
        portal_slug=getattr(user.organization, "portal_slug", None),
    )

    try:
        result_mail = await send_password_reset_email(
            to_email=user.email,
            first_name=user.first_name,
            last_name=user.last_name,
            organization_name=user.organization.name,
            raw_token=raw_token,
            expires_at=user.password_reset_expires_at,
            reset_path=reset_path,
            portal_slug=getattr(user.organization, "portal_slug", None),
        )
        emailed = bool(getattr(result_mail, "sent", False))
        return generic, emailed, (None if emailed else reset_url)
    except EmailError as exc:
        logger.warning("password_reset_email_failed to=%s err=%s", user.email, exc)
        return generic, False, reset_url


async def reset_password(db: AsyncSession, *, token: str, new_password: str) -> None:
    token_hash = _hash_token(token)
    result = await db.execute(
        select(User)
        .where(User.password_reset_token_hash == token_hash)
        .where(User.deleted_at.is_(None))
        .options(selectinload(User.organization), selectinload(User.role))
    )
    user = result.scalar_one_or_none()
    if user is None:
        raise AuthError("Invalid or expired reset token.", status_code=400)
    if user.password_reset_expires_at and user.password_reset_expires_at < datetime.now(
        timezone.utc
    ):
        raise AuthError("Reset token has expired.", status_code=400)
    if user.status != UserStatus.ACTIVE.value:
        raise AuthError("Account cannot reset password in its current status.", status_code=403)

    try:
        role_code = user.role.role_code if user.role else None
        ensure_organization_active_for_login(user.organization, role_code=role_code)
    except OrganizationAccessError as exc:
        raise AuthError(exc.message, status_code=exc.status_code) from exc

    user.password_hash = hash_password(new_password)
    user.password_reset_token_hash = None
    user.password_reset_expires_at = None
    await db.flush()


async def activate_invited_user(
    db: AsyncSession,
    *,
    token: str,
    new_password: str,
) -> User:
    """Activate INVITED TPO or HOD (shared org-portal activate flow)."""
    from app.common.organization_access import ensure_organization_accepts_activation

    token_hash = _hash_token(token)
    result = await db.execute(
        select(User)
        .where(User.activation_token_hash == token_hash)
        .where(User.deleted_at.is_(None))
        .options(selectinload(User.role), selectinload(User.organization))
    )
    user = result.scalar_one_or_none()
    if user is None:
        raise AuthError(
            "Invalid or already-used activation token.",
            status_code=400,
            code="ACTIVATION_TOKEN_INVALID",
        )
    if user.status != UserStatus.INVITED.value:
        raise AuthError(
            "Account is not awaiting activation.",
            status_code=400,
            code="ACCOUNT_NOT_INVITED",
        )
    if user.activation_expires_at and user.activation_expires_at < datetime.now(timezone.utc):
        raise AuthError(
            "Activation token expired. Ask admin to re-invite.",
            status_code=400,
            code="ACTIVATION_TOKEN_EXPIRED",
        )

    if user.organization is not None:
        try:
            ensure_organization_accepts_activation(user.organization)
        except OrganizationAccessError as exc:
            raise AuthError(
                exc.message,
                status_code=exc.status_code,
                code="ORG_SUSPENDED",
            ) from exc

    user.password_hash = hash_password(new_password)
    user.status = UserStatus.ACTIVE.value
    user.activation_token_hash = None
    user.activation_expires_at = None
    # Activate sets the password the user chose — do not force a second change.
    user.must_change_password = False
    await db.flush()
    return user


async def audit_hod_activate(db: AsyncSession, user: User) -> None:
    from app.common.audit import write_audit

    title = dept_admin_title_for(user) or DeptAdminTitle.HOD.value
    action = (
        "coordinator.activate"
        if title == DeptAdminTitle.PLACEMENT_COORDINATOR.value
        else "hod.activate"
    )
    # Backfill title for legacy DEPARTMENT_ADMIN rows activated after migration.
    if user.role and user.role.role_code == RoleCode.DEPARTMENT_ADMIN.value:
        if not getattr(user, "dept_admin_title", None):
            user.dept_admin_title = DeptAdminTitle.HOD.value
            await db.flush()

    await write_audit(
        db,
        organization_id=user.organization_id,
        actor_user_id=user.id,
        action=action,
        entity_type="department",
        entity_id=user.department_id,
        payload={
            "hod_user_id": user.id,
            "department_id": user.department_id,
            "email": user.email,
            "name": f"{user.first_name} {user.last_name}".strip(),
            "dept_admin_title": title,
        },
    )


def token_expires_minutes() -> int:
    return settings.jwt_expire_minutes

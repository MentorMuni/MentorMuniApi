"""Platform portal business logic."""

from __future__ import annotations

import hashlib
import secrets
from calendar import monthrange
from datetime import date, datetime, timedelta, timezone

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.common.organization_access import (
    OrganizationAccessError,
    ensure_organization_accepts_activation,
    is_public_organization,
    reject_create_public_as_suspended,
    reject_suspend_if_public,
)
from app.common.security.passwords import hash_password, verify_password
from app.models.enums import (
    OrganizationStatus,
    PlatformRole,
    PlatformUserStatus,
    RoleCode,
    SubscriptionStatus,
    UserStatus,
)
from app.models.feature_catalog import FeatureCatalog
from app.models.organization import Organization
from app.models.organization_feature import OrganizationFeature
from app.models.organization_subscription import OrganizationSubscription
from app.models.platform_user import PlatformUser
from app.models.role import Role
from app.models.subscription_plan import SubscriptionPlan
from app.models.user import User
from app.organizations.service import _add_months


class PlatformError(Exception):
    def __init__(self, message: str, *, status_code: int = 400) -> None:
        super().__init__(message)
        self.message = message
        self.status_code = status_code


def _hash_token(raw: str) -> str:
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


# =============================================================================
# Auth
# =============================================================================


async def authenticate_platform_user(
    db: AsyncSession,
    *,
    email: str,
    password: str,
) -> PlatformUser:
    result = await db.execute(
        select(PlatformUser).where(PlatformUser.email == email.lower().strip())
    )
    user = result.scalar_one_or_none()
    if user is None or not verify_password(password, user.password_hash):
        raise PlatformError("Invalid credentials.", status_code=401)
    if user.status != PlatformUserStatus.ACTIVE.value:
        raise PlatformError("Account is inactive.", status_code=403)
    return user


async def change_platform_password(
    db: AsyncSession,
    *,
    user: PlatformUser,
    current_password: str,
    new_password: str,
) -> None:
    if not verify_password(current_password, user.password_hash):
        raise PlatformError("Current password is incorrect.")
    user.password_hash = hash_password(new_password)
    user.must_change_password = False
    await db.flush()


# =============================================================================
# Organizations
# =============================================================================


async def create_organization(db: AsyncSession, **fields: object) -> Organization:
    code = str(fields["code"]).strip().upper()
    existing = await db.execute(select(Organization).where(Organization.code == code))
    if existing.scalar_one_or_none():
        raise PlatformError(f"Organization code '{code}' already exists.", status_code=409)

    org_type = str(fields["organization_type"])
    org_status = str(fields.get("status") or OrganizationStatus.ACTIVE.value)
    try:
        reject_create_public_as_suspended(
            organization_type=org_type,
            status=org_status,
        )
    except OrganizationAccessError as exc:
        raise PlatformError(exc.message, status_code=exc.status_code) from exc

    org = Organization(
        name=str(fields["name"]).strip(),
        code=code,
        organization_type=org_type,
        status=org_status,
        contact_person=fields.get("contact_person"),  # type: ignore[arg-type]
        contact_email=str(fields["contact_email"]).lower() if fields.get("contact_email") else None,
        contact_phone=fields.get("contact_phone"),  # type: ignore[arg-type]
        address=fields.get("address"),  # type: ignore[arg-type]
        city=fields.get("city"),  # type: ignore[arg-type]
        state=fields.get("state"),  # type: ignore[arg-type]
        country=fields.get("country"),  # type: ignore[arg-type]
    )
    db.add(org)
    await db.flush()

    # Default: create disabled feature rows for every catalog feature (easy UI toggles).
    catalog = (await db.execute(select(FeatureCatalog))).scalars().all()
    for feat in catalog:
        db.add(
            OrganizationFeature(
                organization_id=org.id,
                feature_id=feat.id,
                enabled=False,
            )
        )
    await db.flush()
    await db.refresh(org)
    return org


async def list_organizations(
    db: AsyncSession,
    *,
    status: str | None = None,
    organization_type: str | None = None,
    search: str | None = None,
) -> tuple[list[Organization], int]:
    stmt = select(Organization)
    count_stmt = select(func.count()).select_from(Organization)

    if status:
        stmt = stmt.where(Organization.status == status)
        count_stmt = count_stmt.where(Organization.status == status)
    if organization_type:
        stmt = stmt.where(Organization.organization_type == organization_type)
        count_stmt = count_stmt.where(Organization.organization_type == organization_type)
    if search:
        like = f"%{search.strip()}%"
        stmt = stmt.where(
            (Organization.name.ilike(like)) | (Organization.code.ilike(like))
        )
        count_stmt = count_stmt.where(
            (Organization.name.ilike(like)) | (Organization.code.ilike(like))
        )

    items = list((await db.execute(stmt.order_by(Organization.id.desc()))).scalars().all())
    total = int((await db.execute(count_stmt)).scalar_one())
    return items, total


async def get_organization(db: AsyncSession, organization_id: int) -> Organization:
    org = await db.get(Organization, organization_id)
    if org is None:
        raise PlatformError("Organization not found.", status_code=404)
    return org


async def update_organization(db: AsyncSession, organization_id: int, **fields: object) -> Organization:
    org = await get_organization(db, organization_id)
    incoming_status = fields.get("status")
    if isinstance(incoming_status, str) or incoming_status is None:
        try:
            reject_suspend_if_public(
                organization=org,
                incoming_status=incoming_status if isinstance(incoming_status, str) else None,
            )
        except OrganizationAccessError as exc:
            raise PlatformError(exc.message, status_code=exc.status_code) from exc

    if "code" in fields and fields["code"] is not None:
        new_code = str(fields["code"]).strip().upper()
        if new_code != org.code:
            if is_public_organization(org):
                raise PlatformError("PUBLIC organization code cannot be changed.", status_code=400)
            clash = await db.execute(
                select(Organization).where(
                    Organization.code == new_code,
                    Organization.id != organization_id,
                )
            )
            if clash.scalar_one_or_none():
                raise PlatformError(
                    f"Organization code '{new_code}' already exists.",
                    status_code=409,
                )
            fields["code"] = new_code

    if "organization_type" in fields and fields["organization_type"] is not None:
        if is_public_organization(org) and str(fields["organization_type"]) != org.organization_type:
            raise PlatformError("PUBLIC organization type cannot be changed.", status_code=400)

    for key, value in fields.items():
        if value is None and key not in {
            "contact_person",
            "contact_email",
            "contact_phone",
            "address",
            "city",
            "state",
            "country",
        }:
            continue
        if key == "contact_email" and value is not None:
            value = str(value).lower()
        setattr(org, key, value)
    await db.flush()
    await db.refresh(org)
    return org


async def delete_organization(db: AsyncSession, organization_id: int) -> Organization:
    """Soft-delete: suspend org and cancel ACTIVE subscriptions. PUBLIC is protected."""
    org = await get_organization(db, organization_id)
    if is_public_organization(org):
        raise PlatformError(
            "The PUBLIC (MentorMuni Public) organization cannot be deleted.",
            status_code=400,
        )

    org.status = OrganizationStatus.SUSPENDED.value
    active = await db.execute(
        select(OrganizationSubscription).where(
            OrganizationSubscription.organization_id == organization_id,
            OrganizationSubscription.status == SubscriptionStatus.ACTIVE.value,
        )
    )
    for row in active.scalars().all():
        row.status = SubscriptionStatus.CANCELLED.value

    await db.flush()
    await db.refresh(org)
    return org


# =============================================================================
# Subscriptions
# =============================================================================


def _sub_to_dict(sub: OrganizationSubscription) -> dict:
    org = sub.organization
    return {
        "id": sub.id,
        "organization_id": sub.organization_id,
        "organization_code": org.code if org else None,
        "organization_name": org.name if org else None,
        "plan_id": sub.plan_id,
        "plan_name": sub.plan_name,
        "student_limit": sub.student_limit,
        "used_students": sub.used_students,
        "start_date": sub.start_date,
        "end_date": sub.end_date,
        "status": sub.status,
        "created_at": sub.created_at,
    }


async def assign_subscription(
    db: AsyncSession,
    *,
    organization_id: int,
    plan_id: int,
    student_limit: int | None = None,
    start_date: date | None = None,
    end_date: date | None = None,
    status: str = SubscriptionStatus.ACTIVE.value,
) -> OrganizationSubscription:
    org = await get_organization(db, organization_id)
    plan = await db.get(SubscriptionPlan, plan_id)
    if plan is None:
        raise PlatformError("Subscription plan not found.", status_code=404)

    if status == SubscriptionStatus.ACTIVE.value:
        active = await db.execute(
            select(OrganizationSubscription).where(
                OrganizationSubscription.organization_id == organization_id,
                OrganizationSubscription.status == SubscriptionStatus.ACTIVE.value,
            )
        )
        for row in active.scalars().all():
            row.status = SubscriptionStatus.EXPIRED.value

    start = start_date or date.today()
    end = end_date or _add_months(start, plan.duration_months)
    if end < start:
        raise PlatformError("end_date must be on or after start_date.")

    sub = OrganizationSubscription(
        organization_id=org.id,
        plan_id=plan.id,
        plan_name=plan.plan_name,
        start_date=start,
        end_date=end,
        student_limit=student_limit or plan.max_students,
        used_students=0,
        status=status,
    )
    db.add(sub)
    await db.flush()

    result = await db.execute(
        select(OrganizationSubscription)
        .where(OrganizationSubscription.id == sub.id)
        .options(selectinload(OrganizationSubscription.organization))
    )
    return result.scalar_one()


async def list_subscriptions(
    db: AsyncSession,
    *,
    organization_id: int | None = None,
    status: str | None = None,
) -> tuple[list[OrganizationSubscription], int]:
    stmt = select(OrganizationSubscription).options(
        selectinload(OrganizationSubscription.organization)
    )
    count_stmt = select(func.count()).select_from(OrganizationSubscription)

    if organization_id is not None:
        stmt = stmt.where(OrganizationSubscription.organization_id == organization_id)
        count_stmt = count_stmt.where(
            OrganizationSubscription.organization_id == organization_id
        )
    if status:
        stmt = stmt.where(OrganizationSubscription.status == status)
        count_stmt = count_stmt.where(OrganizationSubscription.status == status)

    items = list(
        (await db.execute(stmt.order_by(OrganizationSubscription.id.desc()))).scalars().all()
    )
    total = int((await db.execute(count_stmt)).scalar_one())
    return items, total


async def update_subscription(
    db: AsyncSession,
    subscription_id: int,
    **fields: object,
) -> OrganizationSubscription:
    result = await db.execute(
        select(OrganizationSubscription)
        .where(OrganizationSubscription.id == subscription_id)
        .options(selectinload(OrganizationSubscription.organization))
    )
    sub = result.scalar_one_or_none()
    if sub is None:
        raise PlatformError("Subscription not found.", status_code=404)

    plan_id = fields.pop("plan_id", None)
    if plan_id is not None:
        plan = await db.get(SubscriptionPlan, int(plan_id))
        if plan is None:
            raise PlatformError("Subscription plan not found.", status_code=404)
        sub.plan_id = plan.id
        sub.plan_name = plan.plan_name
        if fields.get("student_limit") is None:
            # Keep existing limit unless caller overrides; only seed when unset.
            if not sub.student_limit:
                sub.student_limit = plan.max_students

    new_status = fields.get("status")
    if (
        isinstance(new_status, str)
        and new_status == SubscriptionStatus.ACTIVE.value
        and sub.status != SubscriptionStatus.ACTIVE.value
    ):
        # Reactivating: expire any other ACTIVE row for this org.
        others = await db.execute(
            select(OrganizationSubscription).where(
                OrganizationSubscription.organization_id == sub.organization_id,
                OrganizationSubscription.status == SubscriptionStatus.ACTIVE.value,
                OrganizationSubscription.id != sub.id,
            )
        )
        for row in others.scalars().all():
            row.status = SubscriptionStatus.EXPIRED.value

    for key, value in fields.items():
        if value is None:
            continue
        setattr(sub, key, value)

    if sub.end_date < sub.start_date:
        raise PlatformError("end_date must be on or after start_date.")

    await db.flush()
    await db.refresh(sub)
    return sub


# =============================================================================
# Features
# =============================================================================


async def list_feature_catalog(db: AsyncSession) -> list[FeatureCatalog]:
    result = await db.execute(
        select(FeatureCatalog).order_by(FeatureCatalog.id.asc())
    )
    return list(result.scalars().all())


async def get_org_features(db: AsyncSession, organization_id: int) -> list[dict]:
    await get_organization(db, organization_id)
    catalog = await list_feature_catalog(db)
    existing = await db.execute(
        select(OrganizationFeature).where(
            OrganizationFeature.organization_id == organization_id
        )
    )
    by_id = {row.feature_id: row for row in existing.scalars().all()}

    items: list[dict] = []
    for feat in catalog:
        row = by_id.get(feat.id)
        items.append(
            {
                "feature_id": feat.id,
                "feature_code": feat.feature_code,
                "feature_name": feat.feature_name,
                "enabled": bool(row.enabled) if row else False,
                "configuration_json": row.configuration_json if row else None,
            }
        )
    return items


async def save_org_features(
    db: AsyncSession,
    organization_id: int,
    features: list[dict],
) -> list[dict]:
    await get_organization(db, organization_id)

    for item in features:
        feature_id = int(item["feature_id"])
        feat = await db.get(FeatureCatalog, feature_id)
        if feat is None:
            raise PlatformError(f"Unknown feature_id: {feature_id}", status_code=404)

        result = await db.execute(
            select(OrganizationFeature).where(
                OrganizationFeature.organization_id == organization_id,
                OrganizationFeature.feature_id == feature_id,
            )
        )
        row = result.scalar_one_or_none()
        if row is None:
            row = OrganizationFeature(
                organization_id=organization_id,
                feature_id=feature_id,
                enabled=bool(item["enabled"]),
                configuration_json=item.get("configuration_json"),
            )
            db.add(row)
        else:
            row.enabled = bool(item["enabled"])
            if "configuration_json" in item:
                row.configuration_json = item.get("configuration_json")

    await db.flush()
    return await get_org_features(db, organization_id)


# =============================================================================
# TPO (ORG_ADMIN) invite
# =============================================================================


async def list_tpos(
    db: AsyncSession,
    *,
    organization_id: int | None = None,
) -> tuple[list[User], int]:
    """List all ORG_ADMIN (TPO) accounts for Platform Settings page."""
    stmt = (
        select(User)
        .join(Role, User.role_id == Role.id)
        .where(Role.role_code == RoleCode.ORG_ADMIN.value)
        .options(selectinload(User.organization), selectinload(User.role))
    )
    count_stmt = (
        select(func.count())
        .select_from(User)
        .join(Role, User.role_id == Role.id)
        .where(Role.role_code == RoleCode.ORG_ADMIN.value)
    )
    if organization_id is not None:
        stmt = stmt.where(User.organization_id == organization_id)
        count_stmt = count_stmt.where(User.organization_id == organization_id)

    items = list((await db.execute(stmt.order_by(User.id.desc()))).scalars().unique().all())
    total = int((await db.execute(count_stmt)).scalar_one())
    return items, total


async def reinvite_tpo(
    db: AsyncSession,
    *,
    organization_id: int,
    activation_hours: int = 72,
) -> tuple[User, str, datetime]:
    """
    Regenerate activation token for an existing TPO (INVITED or ACTIVE).
    Use this when Settings shows a TPO already exists and you need a new invite link.
    """
    org = await get_organization(db, organization_id)
    try:
        ensure_organization_accepts_activation(org)
    except OrganizationAccessError as exc:
        raise PlatformError(exc.message, status_code=exc.status_code) from exc

    result = await db.execute(
        select(User)
        .join(Role, User.role_id == Role.id)
        .where(
            User.organization_id == organization_id,
            Role.role_code == RoleCode.ORG_ADMIN.value,
            User.status.in_([UserStatus.ACTIVE.value, UserStatus.INVITED.value]),
        )
        .options(selectinload(User.organization))
    )
    user = result.scalar_one_or_none()
    if user is None:
        raise PlatformError("No ORG_ADMIN (TPO) found for this organization.", status_code=404)

    raw_token = secrets.token_urlsafe(32)
    expires = datetime.now(timezone.utc) + timedelta(hours=activation_hours)
    user.password_hash = None
    user.status = UserStatus.INVITED.value
    user.activation_token_hash = _hash_token(raw_token)
    user.activation_expires_at = expires
    await db.flush()
    await db.refresh(user)
    return user, raw_token, expires


async def update_tpo(
    db: AsyncSession,
    *,
    organization_id: int,
    first_name: str,
    last_name: str,
    email: str,
    username: str,
    mobile: str | None = None,
    activation_hours: int = 72,
    reset_password: bool = True,
) -> tuple[User, str | None, datetime | None]:
    """
    Edit the live TPO in place (same user id).

    Org / departments / HODs / students / subscriptions are untouched.
    When reset_password=True (default): clears old password, sets INVITED,
    returns a new activation token to email to the (possibly new) address.
    """
    org = await get_organization(db, organization_id)
    try:
        ensure_organization_accepts_activation(org)
    except OrganizationAccessError as exc:
        raise PlatformError(exc.message, status_code=exc.status_code) from exc

    result = await db.execute(
        select(User)
        .join(Role, User.role_id == Role.id)
        .where(
            User.organization_id == organization_id,
            Role.role_code == RoleCode.ORG_ADMIN.value,
            User.status.in_([UserStatus.ACTIVE.value, UserStatus.INVITED.value]),
        )
        .options(selectinload(User.organization))
    )
    user = result.scalar_one_or_none()
    if user is None:
        raise PlatformError(
            "No active TPO found for this organization. Create a TPO first.",
            status_code=404,
        )

    email_norm = email.lower().strip()
    username_norm = username.strip()

    dup = await db.execute(
        select(User).where(
            User.organization_id == organization_id,
            User.id != user.id,
            (User.email == email_norm) | (User.username == username_norm),
        )
    )
    if dup.scalar_one_or_none():
        raise PlatformError(
            "Email or username already used by another user in this organization.",
            status_code=409,
        )

    user.first_name = first_name.strip()
    user.last_name = last_name.strip()
    user.email = email_norm
    user.username = username_norm
    user.mobile = mobile

    raw_token: str | None = None
    expires: datetime | None = None
    if reset_password:
        raw_token = secrets.token_urlsafe(32)
        expires = datetime.now(timezone.utc) + timedelta(hours=activation_hours)
        user.password_hash = None
        user.status = UserStatus.INVITED.value
        user.activation_token_hash = _hash_token(raw_token)
        user.activation_expires_at = expires
    else:
        # Details-only update; keep login if already ACTIVE.
        user.activation_token_hash = None
        user.activation_expires_at = None

    await db.flush()
    await db.refresh(user)
    return user, raw_token, expires


async def create_tpo(
    db: AsyncSession,
    *,
    organization_id: int,
    first_name: str,
    last_name: str,
    email: str,
    username: str,
    mobile: str | None = None,
    activation_hours: int = 72,
) -> tuple[User, str, datetime]:
    org = await get_organization(db, organization_id)
    try:
        ensure_organization_accepts_activation(org)
    except OrganizationAccessError as exc:
        raise PlatformError(exc.message, status_code=exc.status_code) from exc

    role_result = await db.execute(
        select(Role).where(Role.role_code == RoleCode.ORG_ADMIN.value)
    )
    role = role_result.scalar_one_or_none()
    if role is None:
        raise PlatformError("ORG_ADMIN role missing. Run migrations/seed.", status_code=500)

    # One active/invited TPO per org is enough for Phase 1.
    existing_tpo = await db.execute(
        select(User)
        .join(Role, User.role_id == Role.id)
        .where(
            User.organization_id == organization_id,
            Role.role_code == RoleCode.ORG_ADMIN.value,
            User.status.in_([UserStatus.ACTIVE.value, UserStatus.INVITED.value]),
        )
    )
    if existing_tpo.scalar_one_or_none():
        raise PlatformError(
            "This organization already has an ORG_ADMIN (TPO). "
            "Use PUT /platform/organizations/{id}/tpo to change details, "
            "or POST .../tpo/reinvite to reset password only.",
            status_code=409,
        )

    email_norm = email.lower().strip()
    username_norm = username.strip()
    dup = await db.execute(
        select(User).where(
            User.organization_id == organization_id,
            (User.email == email_norm) | (User.username == username_norm),
        )
    )
    if dup.scalar_one_or_none():
        raise PlatformError("Email or username already exists in this organization.", status_code=409)

    raw_token = secrets.token_urlsafe(32)
    expires = datetime.now(timezone.utc) + timedelta(hours=activation_hours)

    user = User(
        organization_id=org.id,
        department_id=None,
        role_id=role.id,
        first_name=first_name.strip(),
        last_name=last_name.strip(),
        email=email_norm,
        mobile=mobile,
        username=username_norm,
        password_hash=None,
        status=UserStatus.INVITED.value,
        activation_token_hash=_hash_token(raw_token),
        activation_expires_at=expires,
    )
    db.add(user)
    await db.flush()
    await db.refresh(user)
    return user, raw_token, expires


async def activate_tpo(
    db: AsyncSession,
    *,
    token: str,
    new_password: str,
) -> User:
    token_hash = _hash_token(token)
    result = await db.execute(
        select(User)
        .where(User.activation_token_hash == token_hash)
        .options(selectinload(User.role), selectinload(User.organization))
    )
    user = result.scalar_one_or_none()
    if user is None:
        raise PlatformError(
            "Invalid or already-used activation token.",
            status_code=400,
        )
    if user.status != UserStatus.INVITED.value:
        raise PlatformError("Account is not awaiting activation.", status_code=400)
    if user.activation_expires_at and user.activation_expires_at < datetime.now(timezone.utc):
        raise PlatformError(
            "Activation token expired. Ask platform to re-invite.",
            status_code=400,
        )

    if user.organization is not None:
        try:
            ensure_organization_accepts_activation(user.organization)
        except OrganizationAccessError as exc:
            raise PlatformError(exc.message, status_code=exc.status_code) from exc

    user.password_hash = hash_password(new_password)
    user.status = UserStatus.ACTIVE.value
    user.activation_token_hash = None
    user.activation_expires_at = None
    # Activate sets the password the user chose — do not force a second change.
    if hasattr(user, "must_change_password"):
        user.must_change_password = False
    await db.flush()
    return user


# =============================================================================
# Platform users (MentorMuni employees)
# =============================================================================


async def create_platform_user(db: AsyncSession, **fields: object) -> PlatformUser:
    email = str(fields["email"]).lower().strip()
    existing = await db.execute(select(PlatformUser).where(PlatformUser.email == email))
    if existing.scalar_one_or_none():
        raise PlatformError("Email already exists.", status_code=409)

    user = PlatformUser(
        name=str(fields["name"]).strip(),
        email=email,
        password_hash=hash_password(str(fields["password"])),
        role=str(fields["role"]),
        status=PlatformUserStatus.ACTIVE.value,
        must_change_password=True,
    )
    db.add(user)
    await db.flush()
    await db.refresh(user)
    return user


async def list_platform_users(db: AsyncSession) -> list[PlatformUser]:
    result = await db.execute(select(PlatformUser).order_by(PlatformUser.id.asc()))
    return list(result.scalars().all())


async def update_platform_user(db: AsyncSession, user_id: int, **fields: object) -> PlatformUser:
    user = await db.get(PlatformUser, user_id)
    if user is None:
        raise PlatformError("Platform user not found.", status_code=404)

    if "password" in fields and fields["password"]:
        user.password_hash = hash_password(str(fields["password"]))
        user.must_change_password = True
    if "email" in fields and fields["email"] is not None:
        new_email = str(fields["email"]).lower().strip()
        if new_email != user.email:
            clash = await db.execute(
                select(PlatformUser).where(
                    PlatformUser.email == new_email,
                    PlatformUser.id != user_id,
                )
            )
            if clash.scalar_one_or_none():
                raise PlatformError("Email already exists.", status_code=409)
            user.email = new_email
    for key in ("name", "role", "status"):
        if key in fields and fields[key] is not None:
            setattr(user, key, fields[key])
    await db.flush()
    await db.refresh(user)
    return user


async def delete_platform_user(db: AsyncSession, user_id: int) -> PlatformUser:
    """Soft-delete: set status INACTIVE. No separate invite flow — use POST /users."""
    user = await db.get(PlatformUser, user_id)
    if user is None:
        raise PlatformError("Platform user not found.", status_code=404)
    if user.email.lower() == "mentormuniteam@gmail.com":
        raise PlatformError("Primary platform admin cannot be deleted.", status_code=400)
    user.status = PlatformUserStatus.INACTIVE.value
    await db.flush()
    await db.refresh(user)
    return user


# =============================================================================
# Dashboard (SaaS metrics only — no student PII)
# =============================================================================


async def dashboard_metrics(db: AsyncSession) -> dict:
    org_count = int(
        (await db.execute(select(func.count()).select_from(Organization))).scalar_one()
    )

    students_purchased = int(
        (
            await db.execute(
                select(func.coalesce(func.sum(OrganizationSubscription.student_limit), 0)).where(
                    OrganizationSubscription.status == SubscriptionStatus.ACTIVE.value
                )
            )
        ).scalar_one()
    )

    # Registered students = users with STUDENT role (any status except REJECTED optional;
    # count ACTIVE + PENDING + INVITED as "registered interest").
    students_registered = int(
        (
            await db.execute(
                select(func.count())
                .select_from(User)
                .join(Role, User.role_id == Role.id)
                .where(
                    Role.role_code == RoleCode.STUDENT.value,
                    User.status.in_(
                        [
                            UserStatus.ACTIVE.value,
                            UserStatus.PENDING.value,
                        ]
                    ),
                )
            )
        ).scalar_one()
    )

    active_plans = int(
        (
            await db.execute(
                select(func.count()).select_from(OrganizationSubscription).where(
                    OrganizationSubscription.status == SubscriptionStatus.ACTIVE.value
                )
            )
        ).scalar_one()
    )

    today = date.today()
    month_end = date(today.year, today.month, monthrange(today.year, today.month)[1])
    expiring = int(
        (
            await db.execute(
                select(func.count()).select_from(OrganizationSubscription).where(
                    and_(
                        OrganizationSubscription.status == SubscriptionStatus.ACTIVE.value,
                        OrganizationSubscription.end_date >= today,
                        OrganizationSubscription.end_date <= month_end,
                    )
                )
            )
        ).scalar_one()
    )

    usage_rows = (
        await db.execute(
            select(
                FeatureCatalog.feature_code,
                FeatureCatalog.feature_name,
                func.count(OrganizationFeature.id),
            )
            .outerjoin(
                OrganizationFeature,
                and_(
                    OrganizationFeature.feature_id == FeatureCatalog.id,
                    OrganizationFeature.enabled.is_(True),
                ),
            )
            .group_by(FeatureCatalog.id)
            .order_by(FeatureCatalog.id.asc())
        )
    ).all()

    feature_usage = [
        {
            "feature_code": row[0],
            "feature_name": row[1],
            "enabled_org_count": int(row[2]),
        }
        for row in usage_rows
    ]

    return {
        "organizations": org_count,
        "students_purchased": students_purchased,
        "students_registered": students_registered,
        "active_plans": active_plans,
        "expiring_this_month": expiring,
        "feature_usage": feature_usage,
    }

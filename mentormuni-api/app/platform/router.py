"""
Platform Admin portal routes.

All under /platform/*
Require: X-API-Key + platform Bearer JWT (except login + TPO activate).
"""

from __future__ import annotations

import asyncio

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.email import EmailError
from app.common.email.flows import send_individual_activation_email, send_tpo_activation_email
from app.common.email.templates import build_student_activation_url, build_tpo_activation_url
from app.common.portal_slug import college_portal_base_url
from app.common.security.jwt import create_access_token
from app.core.config import settings
from app.models.enums import PlatformRole
from app.models.organization import Organization
from app.models.platform_user import PlatformUser
from app.platform import service as svc
from app.platform.deps import get_current_platform_user, get_db, require_api_key, require_platform_roles
from app.platform.schemas import (
    ActivateTpoRequest,
    ActivateTpoResponse,
    CreateIndividualRequest,
    CreateIndividualResponse,
    CreateTpoRequest,
    CreateTpoResponse,
    DeactivateOrgAdminResponse,
    FeatureCatalogResponse,
    IndividualListItem,
    IndividualListResponse,
    MessageResponse,
    OrgFeaturesResponse,
    OrgFeaturesSaveRequest,
    PlatformChangePasswordRequest,
    PlatformDashboardResponse,
    PlatformLoginRequest,
    PlatformMeResponse,
    PlatformOrganizationCreate,
    PlatformOrganizationListResponse,
    PlatformOrganizationResponse,
    PlatformOrganizationUpdate,
    PlatformSubscriptionCreate,
    PlatformSubscriptionListResponse,
    PlatformSubscriptionResponse,
    PlatformSubscriptionUpdate,
    PlatformTokenResponse,
    PlatformUserCreate,
    PlatformUserResponse,
    PlatformUserUpdate,
    TpoListItem,
    TpoListResponse,
    UpdateTpoRequest,
)

router = APIRouter(
    prefix="/platform",
    tags=["Platform Admin"],
    dependencies=[Depends(require_api_key)],
)


# =============================================================================
# Auth
# =============================================================================


@router.post("/auth/login", response_model=PlatformTokenResponse)
async def platform_login(
    body: PlatformLoginRequest,
    db: AsyncSession = Depends(get_db),
) -> PlatformTokenResponse:
    from app.common.security.auth_errors import (
        ACCOUNT_INACTIVE,
        INVALID_CREDENTIALS,
        auth_detail,
    )

    try:
        user = await svc.authenticate_platform_user(
            db, email=str(body.email), password=body.password
        )
    except svc.PlatformError as exc:
        code = (
            INVALID_CREDENTIALS
            if exc.status_code == 401
            else ACCOUNT_INACTIVE
            if exc.status_code == 403
            else "PLATFORM_ERROR"
        )
        raise HTTPException(
            status_code=exc.status_code,
            detail=auth_detail(code=code, message=exc.message),
        ) from exc

    token = create_access_token(
        user_id=user.id,
        scope="platform",
        extra={"role": user.role},
    )
    return PlatformTokenResponse(
        access_token=token,
        expires_in_minutes=settings.jwt_expire_minutes,
    )


@router.get("/auth/me", response_model=PlatformMeResponse)
async def platform_me(
    user: PlatformUser = Depends(get_current_platform_user),
) -> PlatformMeResponse:
    return PlatformMeResponse.model_validate(user)


@router.post("/auth/change-password", response_model=MessageResponse)
async def platform_change_password(
    body: PlatformChangePasswordRequest,
    user: PlatformUser = Depends(get_current_platform_user),
    db: AsyncSession = Depends(get_db),
) -> MessageResponse:
    try:
        await svc.change_platform_password(
            db,
            user=user,
            current_password=body.current_password,
            new_password=body.new_password,
        )
    except svc.PlatformError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc
    return MessageResponse(message="Password updated.")


@router.post("/auth/activate-tpo", response_model=ActivateTpoResponse)
async def activate_tpo(
    body: ActivateTpoRequest,
    db: AsyncSession = Depends(get_db),
) -> ActivateTpoResponse:
    """TPO sets password via one-time token (no platform JWT needed)."""
    try:
        user = await svc.activate_tpo(db, token=body.token, new_password=body.new_password)
    except svc.PlatformError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc
    org_code = user.organization.code if user.organization else None
    return ActivateTpoResponse(
        message="Password set. You can log in to the Organization Portal.",
        organization_code=org_code,
    )


# =============================================================================
# Dashboard
# =============================================================================


@router.get("/dashboard", response_model=PlatformDashboardResponse)
async def dashboard(
    _user: PlatformUser = Depends(get_current_platform_user),
    db: AsyncSession = Depends(get_db),
) -> PlatformDashboardResponse:
    data = await svc.dashboard_metrics(db)
    return PlatformDashboardResponse(**data)


# =============================================================================
# Organizations
# =============================================================================


def _org_response(org: Organization) -> PlatformOrganizationResponse:
    data = PlatformOrganizationResponse.model_validate(org)
    if org.portal_slug and str(org.organization_type).upper() != "PUBLIC":
        data.portal_url = college_portal_base_url(org.portal_slug)
    data.has_logo = bool(org.logo_content_type)
    data.logo_updated_at = org.logo_updated_at
    return data


@router.post("/organizations", response_model=PlatformOrganizationResponse, status_code=201)
async def create_organization(
    body: PlatformOrganizationCreate,
    _user: PlatformUser = Depends(get_current_platform_user),
    db: AsyncSession = Depends(get_db),
) -> PlatformOrganizationResponse:
    try:
        org = await svc.create_organization(db, **body.model_dump())
    except svc.PlatformError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc
    return _org_response(org)


@router.get("/organizations", response_model=PlatformOrganizationListResponse)
async def list_organizations(
    status: str | None = Query(default=None),
    organization_type: str | None = Query(default=None),
    search: str | None = Query(default=None),
    _user: PlatformUser = Depends(get_current_platform_user),
    db: AsyncSession = Depends(get_db),
) -> PlatformOrganizationListResponse:
    items, total = await svc.list_organizations(
        db,
        status=status,
        organization_type=organization_type,
        search=search,
    )
    return PlatformOrganizationListResponse(
        items=[_org_response(o) for o in items],
        total=total,
    )


@router.get("/organizations/{organization_id}", response_model=PlatformOrganizationResponse)
async def get_organization(
    organization_id: int,
    _user: PlatformUser = Depends(get_current_platform_user),
    db: AsyncSession = Depends(get_db),
) -> PlatformOrganizationResponse:
    try:
        org = await svc.get_organization(db, organization_id)
    except svc.PlatformError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc
    return _org_response(org)


@router.put("/organizations/{organization_id}", response_model=PlatformOrganizationResponse)
async def update_organization(
    organization_id: int,
    body: PlatformOrganizationUpdate,
    _user: PlatformUser = Depends(get_current_platform_user),
    db: AsyncSession = Depends(get_db),
) -> PlatformOrganizationResponse:
    try:
        org = await svc.update_organization(
            db, organization_id, **body.model_dump(exclude_unset=True)
        )
    except svc.PlatformError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc
    return _org_response(org)


@router.delete("/organizations/{organization_id}", response_model=PlatformOrganizationResponse)
async def delete_organization(
    organization_id: int,
    _user: PlatformUser = Depends(get_current_platform_user),
    db: AsyncSession = Depends(get_db),
) -> PlatformOrganizationResponse:
    """Soft-delete: set status=SUSPENDED and cancel ACTIVE subscriptions."""
    try:
        org = await svc.delete_organization(db, organization_id)
    except svc.PlatformError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc
    return _org_response(org)


@router.post(
    "/organizations/{organization_id}/logo",
    response_model=PlatformOrganizationResponse,
)
async def upload_organization_logo(
    organization_id: int,
    file: UploadFile = File(...),
    _user: PlatformUser = Depends(get_current_platform_user),
    db: AsyncSession = Depends(get_db),
) -> PlatformOrganizationResponse:
    """Upload college crest/logo (PNG/JPEG/WebP/SVG, max 512 KB). Stored in Postgres."""
    from app.platform import org_logo as logo_svc

    raw = await file.read()
    try:
        org = await logo_svc.set_organization_logo(
            db,
            organization_id,
            data=raw,
            content_type=file.content_type or "",
        )
    except svc.PlatformError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc
    return _org_response(org)


@router.delete(
    "/organizations/{organization_id}/logo",
    response_model=PlatformOrganizationResponse,
)
async def delete_organization_logo(
    organization_id: int,
    _user: PlatformUser = Depends(get_current_platform_user),
    db: AsyncSession = Depends(get_db),
) -> PlatformOrganizationResponse:
    from app.platform import org_logo as logo_svc

    try:
        org = await logo_svc.clear_organization_logo(db, organization_id)
    except svc.PlatformError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc
    return _org_response(org)


# =============================================================================
# Subscriptions
# =============================================================================


@router.post("/subscriptions", response_model=PlatformSubscriptionResponse, status_code=201)
async def create_subscription(
    body: PlatformSubscriptionCreate,
    _user: PlatformUser = Depends(get_current_platform_user),
    db: AsyncSession = Depends(get_db),
) -> PlatformSubscriptionResponse:
    try:
        sub = await svc.assign_subscription(
            db,
            organization_id=body.organization_id,
            plan_id=body.plan_id,
            student_limit=body.student_limit,
            start_date=body.start_date,
            end_date=body.end_date,
            status=body.status,
        )
    except svc.PlatformError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc
    return PlatformSubscriptionResponse(**svc._sub_to_dict(sub))


@router.get("/subscriptions", response_model=PlatformSubscriptionListResponse)
async def list_subscriptions(
    organization_id: int | None = Query(default=None),
    status: str | None = Query(default=None),
    _user: PlatformUser = Depends(get_current_platform_user),
    db: AsyncSession = Depends(get_db),
) -> PlatformSubscriptionListResponse:
    items, total = await svc.list_subscriptions(
        db, organization_id=organization_id, status=status
    )
    return PlatformSubscriptionListResponse(
        items=[PlatformSubscriptionResponse(**svc._sub_to_dict(s)) for s in items],
        total=total,
    )


@router.put("/subscriptions/{subscription_id}", response_model=PlatformSubscriptionResponse)
async def update_subscription(
    subscription_id: int,
    body: PlatformSubscriptionUpdate,
    _user: PlatformUser = Depends(get_current_platform_user),
    db: AsyncSession = Depends(get_db),
) -> PlatformSubscriptionResponse:
    try:
        sub = await svc.update_subscription(
            db, subscription_id, **body.model_dump(exclude_unset=True)
        )
    except svc.PlatformError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc
    return PlatformSubscriptionResponse(**svc._sub_to_dict(sub))


# =============================================================================
# Feature Management
# =============================================================================


@router.get("/feature-catalog", response_model=list[FeatureCatalogResponse])
async def feature_catalog(
    _user: PlatformUser = Depends(get_current_platform_user),
    db: AsyncSession = Depends(get_db),
) -> list[FeatureCatalogResponse]:
    items = await svc.list_feature_catalog(db)
    return [FeatureCatalogResponse.model_validate(f) for f in items]


@router.get(
    "/organizations/{organization_id}/features",
    response_model=OrgFeaturesResponse,
)
async def get_org_features(
    organization_id: int,
    _user: PlatformUser = Depends(get_current_platform_user),
    db: AsyncSession = Depends(get_db),
) -> OrgFeaturesResponse:
    try:
        features = await svc.get_org_features(db, organization_id)
    except svc.PlatformError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc
    return OrgFeaturesResponse(organization_id=organization_id, features=features)


@router.put(
    "/organizations/{organization_id}/features",
    response_model=OrgFeaturesResponse,
)
async def save_org_features(
    organization_id: int,
    body: OrgFeaturesSaveRequest,
    _user: PlatformUser = Depends(get_current_platform_user),
    db: AsyncSession = Depends(get_db),
) -> OrgFeaturesResponse:
    try:
        features = await svc.save_org_features(
            db,
            organization_id,
            [f.model_dump() for f in body.features],
        )
    except svc.PlatformError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc
    return OrgFeaturesResponse(organization_id=organization_id, features=features)


# =============================================================================
# Org Admin (ORG_ADMIN) — TPO / Dean / Director (same access)
# =============================================================================


def _org_admin_title(user) -> str:
    return getattr(user, "org_admin_title", None) or "TPO"


def _tpo_list_item(user) -> TpoListItem:
    title = _org_admin_title(user)
    return TpoListItem(
        id=user.id,
        organization_id=user.organization_id,
        organization_code=user.organization.code if user.organization else None,
        organization_name=user.organization.name if user.organization else None,
        first_name=user.first_name,
        last_name=user.last_name,
        email=user.email,
        username=user.username,
        mobile=user.mobile,
        status=user.status,
        title=title,
        is_primary=title == "TPO",
        display_role="Org Admin",
        created_at=user.created_at,
        activation_pending=user.status == "INVITED",
    )


def _create_tpo_response(
    *,
    user,
    raw_token: str,
    expires,
    message: str,
    email_sent: bool = False,
    email_skipped: bool = False,
    email_detail: str = "",
    portal_slug: str | None = None,
) -> CreateTpoResponse:
    title = _org_admin_title(user)
    return CreateTpoResponse(
        id=user.id,
        organization_id=user.organization_id,
        first_name=user.first_name,
        last_name=user.last_name,
        email=user.email,
        username=user.username,
        status=user.status,
        title=title,
        is_primary=title == "TPO",
        display_role="Org Admin",
        activation_token=raw_token,
        activation_url=(
            build_tpo_activation_url(raw_token, portal_slug=portal_slug) if raw_token else ""
        ),
        activation_expires_at=expires,
        message=message,
        email_sent=email_sent,
        email_skipped=email_skipped,
        email_detail=email_detail,
    )


@router.get("/tpo", response_model=TpoListResponse)
async def list_tpos(
    organization_id: int | None = Query(default=None),
    _user: PlatformUser = Depends(get_current_platform_user),
    db: AsyncSession = Depends(get_db),
) -> TpoListResponse:
    """List Org Admins (TPO / Dean / Director)."""
    items, total = await svc.list_tpos(db, organization_id=organization_id)
    return TpoListResponse(items=[_tpo_list_item(u) for u in items], total=total)


@router.get("/organizations/{organization_id}/tpo", response_model=TpoListResponse)
async def list_org_tpo(
    organization_id: int,
    _user: PlatformUser = Depends(get_current_platform_user),
    db: AsyncSession = Depends(get_db),
) -> TpoListResponse:
    items, total = await svc.list_tpos(db, organization_id=organization_id)
    return TpoListResponse(items=[_tpo_list_item(u) for u in items], total=total)


async def _build_tpo_invite_response(
    *,
    user,
    raw_token: str,
    expires,
    organization_name: str,
    is_reinvite: bool,
    is_update: bool = False,
    portal_slug: str | None = None,
) -> CreateTpoResponse:
    """Attach email delivery result; never fail the invite if SMTP/Resend is down."""
    email_sent = False
    email_skipped = False
    email_detail = ""
    role_label = svc.org_admin_display_label(getattr(user, "org_admin_title", None))
    short_label = "Org Admin"
    email_budget = float(min(settings.smtp_timeout_seconds + 3, 20))
    try:
        result = await asyncio.wait_for(
            send_tpo_activation_email(
                to_email=user.email,
                first_name=user.first_name,
                last_name=user.last_name,
                username=user.username,
                organization_name=organization_name,
                raw_token=raw_token,
                expires_at=expires,
                is_reinvite=is_reinvite or is_update,
                role_label=role_label,
                portal_slug=portal_slug,
            ),
            timeout=email_budget,
        )
        email_sent = result.sent
        email_skipped = result.skipped
        email_detail = result.detail
    except asyncio.TimeoutError:
        email_sent = False
        email_skipped = False
        email_detail = (
            "Email send timed out. Share the activation link or token manually."
        )
    except EmailError as exc:
        email_sent = False
        email_skipped = False
        email_detail = exc.message

    if is_update:
        verb_ok = f"{short_label} details updated and activation email sent to the new address."
        verb_skip = f"{short_label} details updated. Email is disabled; share activation_token manually."
        verb_fail = f"{short_label} details updated but activation email failed. Share activation_token manually."
    elif is_reinvite:
        verb_ok = f"{short_label} re-invited and activation email sent."
        verb_skip = f"{short_label} re-invited. Email is disabled; share activation_token manually."
        verb_fail = f"{short_label} re-invited but activation email failed. Share activation_token manually."
    else:
        verb_ok = f"{short_label} ({role_label}) invited and activation email sent."
        verb_skip = f"{short_label} invited. Email is disabled; share activation_token manually."
        verb_fail = f"{short_label} invited but activation email failed. Share activation_token manually."

    if email_sent:
        message = verb_ok
    elif email_skipped:
        message = (
            f"{verb_skip} "
            "Set password via POST /platform/auth/activate-tpo."
        )
    else:
        message = f"{verb_fail} ({email_detail})"

    return _create_tpo_response(
        user=user,
        raw_token=raw_token,
        expires=expires,
        message=message,
        email_sent=email_sent,
        email_skipped=email_skipped,
        email_detail=email_detail,
        portal_slug=portal_slug,
    )


@router.post(
    "/organizations/{organization_id}/tpo",
    response_model=CreateTpoResponse,
    status_code=201,
)
async def create_tpo(
    organization_id: int,
    body: CreateTpoRequest,
    _user: PlatformUser = Depends(get_current_platform_user),
    db: AsyncSession = Depends(get_db),
) -> CreateTpoResponse:
    try:
        user, raw_token, expires = await svc.create_tpo(
            db,
            organization_id=organization_id,
            first_name=body.first_name,
            last_name=body.last_name,
            email=str(body.email),
            username=body.username,
            mobile=body.mobile,
            title=body.title,
            activation_hours=body.activation_hours,
        )
        org = await svc.get_organization(db, organization_id)
    except svc.PlatformError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc

    return await _build_tpo_invite_response(
        user=user,
        raw_token=raw_token,
        expires=expires,
        organization_name=org.name,
        is_reinvite=False,
        portal_slug=org.portal_slug,
    )


@router.post(
    "/organizations/{organization_id}/tpo/reinvite",
    response_model=CreateTpoResponse,
)
async def reinvite_tpo(
    organization_id: int,
    activation_hours: int = Query(default=72, ge=1, le=168),
    user_id: int | None = Query(default=None),
    _user: PlatformUser = Depends(get_current_platform_user),
    db: AsyncSession = Depends(get_db),
) -> CreateTpoResponse:
    """Regenerate activation token. Pass user_id when multiple Org Admins exist."""
    try:
        user, raw_token, expires = await svc.reinvite_tpo(
            db,
            organization_id=organization_id,
            user_id=user_id,
            activation_hours=activation_hours,
        )
        org = await svc.get_organization(db, organization_id)
    except svc.PlatformError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc

    return await _build_tpo_invite_response(
        user=user,
        raw_token=raw_token,
        expires=expires,
        organization_name=org.name,
        is_reinvite=True,
        portal_slug=org.portal_slug,
    )


@router.put(
    "/organizations/{organization_id}/tpo",
    response_model=CreateTpoResponse,
)
async def update_tpo(
    organization_id: int,
    body: UpdateTpoRequest,
    _user: PlatformUser = Depends(get_current_platform_user),
    db: AsyncSession = Depends(get_db),
) -> CreateTpoResponse:
    """
    Change Org Admin details (same user id).

    Pass body.user_id when the org has TPO + Dean + Director.
    """
    try:
        user, raw_token, expires = await svc.update_tpo(
            db,
            organization_id=organization_id,
            user_id=body.user_id,
            first_name=body.first_name,
            last_name=body.last_name,
            email=str(body.email),
            username=body.username,
            mobile=body.mobile,
            title=body.title,
            activation_hours=body.activation_hours,
            reset_password=body.reset_password,
        )
        org = await svc.get_organization(db, organization_id)
    except svc.PlatformError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc

    if body.reset_password and raw_token and expires:
        return await _build_tpo_invite_response(
            user=user,
            raw_token=raw_token,
            expires=expires,
            organization_name=org.name,
            is_reinvite=False,
            is_update=True,
            portal_slug=org.portal_slug,
        )

    return _create_tpo_response(
        user=user,
        raw_token="",
        expires=user.updated_at,
        message="Org Admin details updated. Password was not reset.",
        email_sent=False,
        email_skipped=True,
        email_detail="reset_password=false",
    )


@router.post(
    "/organizations/{organization_id}/tpo/{user_id}/deactivate",
    response_model=DeactivateOrgAdminResponse,
)
async def deactivate_org_admin(
    organization_id: int,
    user_id: int,
    _user: PlatformUser = Depends(get_current_platform_user),
    db: AsyncSession = Depends(get_db),
) -> DeactivateOrgAdminResponse:
    """Deactivate one Org Admin; others and org data stay intact."""
    try:
        user = await svc.deactivate_org_admin(
            db, organization_id=organization_id, user_id=user_id
        )
    except svc.PlatformError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc
    title = _org_admin_title(user)
    return DeactivateOrgAdminResponse(
        id=user.id,
        organization_id=user.organization_id,
        title=title,
        status=user.status,
        message=f"Org Admin ({title}) deactivated. Other admins are unchanged.",
    )


# =============================================================================
# Individuals (PUBLIC students — separate from college Organizations)
# =============================================================================


def _individual_list_item(user) -> IndividualListItem:
    return IndividualListItem(
        id=user.id,
        first_name=user.first_name,
        last_name=user.last_name,
        email=user.email,
        username=user.username,
        mobile=user.mobile,
        status=user.status,
        college_name=user.college_name,
        course_or_branch=user.course_or_branch,
        batch_year=user.batch_year,
        roll_number=user.roll_number,
        created_at=user.created_at,
        activation_pending=user.status == "INVITED",
    )


def _create_individual_response(
    *,
    user,
    raw_token: str,
    expires,
    message: str,
    email_sent: bool = False,
    email_skipped: bool = False,
    email_detail: str = "",
) -> CreateIndividualResponse:
    return CreateIndividualResponse(
        id=user.id,
        first_name=user.first_name,
        last_name=user.last_name,
        email=user.email,
        username=user.username,
        status=user.status,
        college_name=user.college_name,
        course_or_branch=user.course_or_branch,
        batch_year=user.batch_year,
        roll_number=user.roll_number,
        activation_token=raw_token,
        activation_url=build_student_activation_url(raw_token) if raw_token else "",
        activation_expires_at=expires,
        message=message,
        email_sent=email_sent,
        email_skipped=email_skipped,
        email_detail=email_detail,
    )


async def _build_individual_invite_response(
    *,
    user,
    raw_token: str,
    expires,
    is_reinvite: bool,
) -> CreateIndividualResponse:
    email_sent = False
    email_skipped = False
    email_detail = ""
    email_budget = float(min(settings.smtp_timeout_seconds + 3, 20))
    try:
        result = await asyncio.wait_for(
            send_individual_activation_email(
                to_email=user.email,
                first_name=user.first_name,
                last_name=user.last_name,
                username=user.username,
                raw_token=raw_token,
                expires_at=expires,
                is_reinvite=is_reinvite,
            ),
            timeout=email_budget,
        )
        email_sent = result.sent
        email_skipped = result.skipped
        email_detail = result.detail
    except asyncio.TimeoutError:
        email_sent = False
        email_skipped = False
        email_detail = "Email send timed out. Share the activation link or token manually."
    except EmailError as exc:
        email_sent = False
        email_skipped = False
        email_detail = exc.message

    if is_reinvite:
        verb_ok = "Individual student re-invited and activation email sent."
        verb_skip = "Individual student re-invited. Email is disabled; share activation_url manually."
        verb_fail = "Individual student re-invited but activation email failed. Share activation_url manually."
    else:
        verb_ok = "Individual student invited and activation email sent."
        verb_skip = "Individual student invited. Email is disabled; share activation_url manually."
        verb_fail = "Individual student invited but activation email failed. Share activation_url manually."

    if email_sent:
        message = verb_ok
    elif email_skipped:
        message = f"{verb_skip} Set password via POST /auth/activate-student."
    else:
        message = f"{verb_fail} ({email_detail})"

    return _create_individual_response(
        user=user,
        raw_token=raw_token,
        expires=expires,
        message=message,
        email_sent=email_sent,
        email_skipped=email_skipped,
        email_detail=email_detail,
    )


@router.get("/individuals", response_model=IndividualListResponse)
async def list_individuals(
    q: str | None = Query(default=None),
    status: str | None = Query(default=None),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=500),
    _user: PlatformUser = Depends(get_current_platform_user),
    db: AsyncSession = Depends(get_db),
) -> IndividualListResponse:
    """List individual (PUBLIC) students — separate from college Organizations."""
    try:
        items, total = await svc.list_individuals(
            db, q=q, status=status, skip=skip, limit=limit
        )
    except svc.PlatformError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc
    return IndividualListResponse(
        items=[_individual_list_item(u) for u in items],
        total=total,
    )


@router.post("/individuals", response_model=CreateIndividualResponse, status_code=201)
async def create_individual(
    body: CreateIndividualRequest,
    _user: PlatformUser = Depends(get_current_platform_user),
    db: AsyncSession = Depends(get_db),
) -> CreateIndividualResponse:
    """
    Staff-provision an individual student under MentorMuni Public.
    Sends set-password email (student portal). Payment/checkout is out of scope here.
    """
    try:
        user, raw_token, expires = await svc.create_individual(
            db,
            first_name=body.first_name,
            last_name=body.last_name,
            email=str(body.email),
            mobile=body.mobile,
            username=body.username,
            college_name=body.college_name,
            course_or_branch=body.course_or_branch,
            batch_year=body.batch_year,
            roll_number=body.roll_number,
            activation_hours=body.activation_hours,
        )
    except svc.PlatformError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc

    return await _build_individual_invite_response(
        user=user,
        raw_token=raw_token,
        expires=expires,
        is_reinvite=False,
    )


@router.post(
    "/individuals/{user_id}/reinvite",
    response_model=CreateIndividualResponse,
)
async def reinvite_individual(
    user_id: int,
    activation_hours: int = Query(default=72, ge=1, le=168),
    _user: PlatformUser = Depends(get_current_platform_user),
    db: AsyncSession = Depends(get_db),
) -> CreateIndividualResponse:
    try:
        user, raw_token, expires = await svc.reinvite_individual(
            db, user_id=user_id, activation_hours=activation_hours
        )
    except svc.PlatformError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc

    return await _build_individual_invite_response(
        user=user,
        raw_token=raw_token,
        expires=expires,
        is_reinvite=True,
    )


@router.post("/individuals/{user_id}/block", response_model=IndividualListItem)
async def block_individual(
    user_id: int,
    _user: PlatformUser = Depends(get_current_platform_user),
    db: AsyncSession = Depends(get_db),
) -> IndividualListItem:
    try:
        user = await svc.block_individual(db, user_id=user_id)
    except svc.PlatformError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc
    return _individual_list_item(user)


# =============================================================================
# Platform Users (MentorMuni employees)
# =============================================================================


@router.post("/users", response_model=PlatformUserResponse, status_code=201)
async def create_platform_user(
    body: PlatformUserCreate,
    _user: PlatformUser = Depends(
        require_platform_roles(PlatformRole.PLATFORM_ADMIN.value)
    ),
    db: AsyncSession = Depends(get_db),
) -> PlatformUserResponse:
    try:
        user = await svc.create_platform_user(db, **body.model_dump())
    except svc.PlatformError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc
    return PlatformUserResponse.model_validate(user)


@router.get("/users", response_model=list[PlatformUserResponse])
async def list_platform_users(
    _user: PlatformUser = Depends(get_current_platform_user),
    db: AsyncSession = Depends(get_db),
) -> list[PlatformUserResponse]:
    items = await svc.list_platform_users(db)
    return [PlatformUserResponse.model_validate(u) for u in items]


@router.put("/users/{user_id}", response_model=PlatformUserResponse)
async def update_platform_user(
    user_id: int,
    body: PlatformUserUpdate,
    _user: PlatformUser = Depends(
        require_platform_roles(PlatformRole.PLATFORM_ADMIN.value)
    ),
    db: AsyncSession = Depends(get_db),
) -> PlatformUserResponse:
    try:
        user = await svc.update_platform_user(
            db, user_id, **body.model_dump(exclude_unset=True)
        )
    except svc.PlatformError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc
    return PlatformUserResponse.model_validate(user)


@router.delete("/users/{user_id}", response_model=PlatformUserResponse)
async def delete_platform_user(
    user_id: int,
    _user: PlatformUser = Depends(
        require_platform_roles(PlatformRole.PLATFORM_ADMIN.value)
    ),
    db: AsyncSession = Depends(get_db),
) -> PlatformUserResponse:
    """Soft-delete: set status=INACTIVE. Invite = POST /platform/users with temp password."""
    try:
        user = await svc.delete_platform_user(db, user_id)
    except svc.PlatformError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc
    return PlatformUserResponse.model_validate(user)

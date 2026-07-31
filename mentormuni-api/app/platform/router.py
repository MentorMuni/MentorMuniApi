"""
Platform Admin portal routes.

All under /platform/*
Require: X-API-Key + platform Bearer JWT (except login + TPO activate).
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.email import EmailError
from app.common.email.flows import send_tpo_activation_email
from app.common.email.templates import build_tpo_activation_url
from app.common.security.jwt import create_access_token
from app.core.config import settings
from app.models.enums import PlatformRole
from app.models.platform_user import PlatformUser
from app.platform import service as svc
from app.platform.deps import get_current_platform_user, get_db, require_api_key, require_platform_roles
from app.platform.schemas import (
    ActivateTpoRequest,
    CreateTpoRequest,
    CreateTpoResponse,
    FeatureCatalogResponse,
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
    try:
        user = await svc.authenticate_platform_user(
            db, email=str(body.email), password=body.password
        )
    except svc.PlatformError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc

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


@router.post("/auth/activate-tpo", response_model=MessageResponse)
async def activate_tpo(
    body: ActivateTpoRequest,
    db: AsyncSession = Depends(get_db),
) -> MessageResponse:
    """TPO sets password via one-time token (no platform JWT needed)."""
    try:
        await svc.activate_tpo(db, token=body.token, new_password=body.new_password)
    except svc.PlatformError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc
    return MessageResponse(message="Password set. You can log in to the Organization Portal.")


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
    return PlatformOrganizationResponse.model_validate(org)


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
        items=[PlatformOrganizationResponse.model_validate(o) for o in items],
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
    return PlatformOrganizationResponse.model_validate(org)


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
    return PlatformOrganizationResponse.model_validate(org)


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
# TPO (ORG_ADMIN) — Create / List / Reinvite
# =============================================================================


def _tpo_list_item(user) -> TpoListItem:
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
        created_at=user.created_at,
        activation_pending=user.status == "INVITED",
    )


@router.get("/tpo", response_model=TpoListResponse)
async def list_tpos(
    organization_id: int | None = Query(default=None),
    _user: PlatformUser = Depends(get_current_platform_user),
    db: AsyncSession = Depends(get_db),
) -> TpoListResponse:
    """Settings page: list all ORG_ADMIN (TPO) accounts."""
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
) -> CreateTpoResponse:
    """Attach email delivery result; never fail the invite if SMTP is down."""
    email_sent = False
    email_skipped = False
    email_detail = ""
    try:
        result = await send_tpo_activation_email(
            to_email=user.email,
            first_name=user.first_name,
            last_name=user.last_name,
            username=user.username,
            organization_name=organization_name,
            raw_token=raw_token,
            expires_at=expires,
            is_reinvite=is_reinvite or is_update,
        )
        email_sent = result.sent
        email_skipped = result.skipped
        email_detail = result.detail
    except EmailError as exc:
        email_sent = False
        email_skipped = False
        email_detail = exc.message

    if is_update:
        verb_ok = "TPO details updated and activation email sent to the new address."
        verb_skip = "TPO details updated. Email is disabled; share activation_token manually."
        verb_fail = "TPO details updated but activation email failed. Share activation_token manually."
    elif is_reinvite:
        verb_ok = "TPO re-invited and activation email sent."
        verb_skip = "TPO re-invited. Email is disabled; share activation_token manually."
        verb_fail = "TPO re-invited but activation email failed. Share activation_token manually."
    else:
        verb_ok = "TPO invited and activation email sent."
        verb_skip = "TPO invited. Email is disabled; share activation_token manually."
        verb_fail = "TPO invited but activation email failed. Share activation_token manually."

    if email_sent:
        message = verb_ok
    elif email_skipped:
        message = (
            f"{verb_skip} "
            "TPO sets password via POST /platform/auth/activate-tpo."
        )
    else:
        message = f"{verb_fail} ({email_detail})"

    return CreateTpoResponse(
        id=user.id,
        organization_id=user.organization_id,
        first_name=user.first_name,
        last_name=user.last_name,
        email=user.email,
        username=user.username,
        status=user.status,
        activation_token=raw_token,
        activation_url=build_tpo_activation_url(raw_token),
        activation_expires_at=expires,
        message=message,
        email_sent=email_sent,
        email_skipped=email_skipped,
        email_detail=email_detail,
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
    )


@router.post(
    "/organizations/{organization_id}/tpo/reinvite",
    response_model=CreateTpoResponse,
)
async def reinvite_tpo(
    organization_id: int,
    activation_hours: int = Query(default=72, ge=1, le=168),
    _user: PlatformUser = Depends(get_current_platform_user),
    db: AsyncSession = Depends(get_db),
) -> CreateTpoResponse:
    """Regenerate activation token when TPO already exists (same person, password reset)."""
    try:
        user, raw_token, expires = await svc.reinvite_tpo(
            db,
            organization_id=organization_id,
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
    Change TPO details on the existing account (same user id).

    When a TPO leaves: update name/email/username and (by default) force a new
    password via activation email. College data and dashboard stay on this org.
    """
    try:
        user, raw_token, expires = await svc.update_tpo(
            db,
            organization_id=organization_id,
            first_name=body.first_name,
            last_name=body.last_name,
            email=str(body.email),
            username=body.username,
            mobile=body.mobile,
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
        )

    # Details-only update (no password reset / no email).
    return CreateTpoResponse(
        id=user.id,
        organization_id=user.organization_id,
        first_name=user.first_name,
        last_name=user.last_name,
        email=user.email,
        username=user.username,
        status=user.status,
        activation_token="",
        activation_url="",
        activation_expires_at=user.updated_at,
        message="TPO details updated. Password was not reset.",
        email_sent=False,
        email_skipped=True,
        email_detail="reset_password=false",
    )


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

"""Company Intelligence service: cache lookup + background LLM generation."""

from __future__ import annotations

import logging
import re
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from fastapi import HTTPException
from sqlalchemy import or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.company_intelligence.constants import (
    CURATED_COMPANIES,
    DEFAULT_COUNTRY,
    DEFAULT_ROLE,
    GENERATING_STALE_SECONDS,
    PROMPT_VERSION,
    STATUS_FAILED,
    STATUS_GENERATING,
    STATUS_READY,
    STATUS_UNKNOWN,
)
from app.company_intelligence.models import CompanyIntelligence
from app.company_intelligence.schemas import (
    CompanyIntelListOut,
    CompanyIntelOut,
    CompanyIntelSummaryOut,
)
from app.company_intelligence.validate import (
    CompanyIntelValidationError,
    validate_company_intelligence,
)
from app.models.enums import RoleCode
from app.models.user import User

logger = logging.getLogger("company_intelligence")


def _iso(dt: Optional[datetime]) -> Optional[str]:
    if dt is None:
        return None
    return dt.astimezone(timezone.utc).isoformat()


def normalize_key(value: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", (value or "").strip().lower())
    return s.strip("-")[:160] or "unknown"


def build_slug(company: str, role: str, country: str) -> str:
    return f"{normalize_key(company)}--{normalize_key(role)}--{normalize_key(country)}"[:220]


def _ensure_student(user: User) -> None:
    code = user.role.role_code if user.role else None
    if code != RoleCode.STUDENT.value:
        raise HTTPException(status_code=403, detail="Student role required.")


def _summary(row: CompanyIntelligence) -> CompanyIntelSummaryOut:
    payload = row.payload_json if isinstance(row.payload_json, dict) else {}
    profile = payload.get("company_profile") if isinstance(payload.get("company_profile"), dict) else {}
    process = payload.get("hiring_process") if isinstance(payload.get("hiring_process"), list) else []
    return CompanyIntelSummaryOut(
        id=row.id,
        slug=row.slug,
        company=row.company_name,
        role=row.role_name,
        country=row.country,
        status=row.status,
        overall_confidence=row.overall_confidence,
        evidence_strength=row.evidence_strength,
        last_updated_estimate=row.last_updated_estimate,
        hiring_type=str(profile.get("hiring_type") or "") or None,
        technical_depth=str(profile.get("technical_depth") or "") or None,
        rounds_count=len(process) if process else None,
    )


def serialize(row: CompanyIntelligence) -> CompanyIntelOut:
    return CompanyIntelOut(
        id=row.id,
        slug=row.slug,
        company=row.company_name,
        role=row.role_name,
        country=row.country,
        status=row.status,
        overall_confidence=row.overall_confidence,
        evidence_strength=row.evidence_strength,
        last_updated_estimate=row.last_updated_estimate,
        error_message=row.error_message,
        prompt_version=row.prompt_version,
        model=row.model,
        completed_at=_iso(row.completed_at),
        payload=row.payload_json if row.status == STATUS_READY else None,
    )


async def list_intelligence(
    db: AsyncSession,
    user: User,
    *,
    q: str | None = None,
    limit: int = 24,
) -> CompanyIntelListOut:
    _ensure_student(user)
    limit = max(1, min(int(limit or 24), 50))
    stmt = select(CompanyIntelligence).where(CompanyIntelligence.status == STATUS_READY)
    if q and q.strip():
        term = f"%{q.strip()}%"
        stmt = stmt.where(
            or_(
                CompanyIntelligence.company_name.ilike(term),
                CompanyIntelligence.role_name.ilike(term),
                CompanyIntelligence.slug.ilike(term),
            )
        )
    stmt = stmt.order_by(CompanyIntelligence.company_name.asc()).limit(limit)
    rows = (await db.execute(stmt)).scalars().all()
    return CompanyIntelListOut(
        items=[_summary(r) for r in rows],
        catalog=list(CURATED_COMPANIES),
    )


async def get_by_slug(db: AsyncSession, user: User, slug: str) -> CompanyIntelOut:
    _ensure_student(user)
    row = (
        await db.execute(select(CompanyIntelligence).where(CompanyIntelligence.slug == slug.strip()))
    ).scalar_one_or_none()
    if row is None:
        raise HTTPException(status_code=404, detail="Company intelligence not found.")
    return serialize(row)


async def get_by_id(db: AsyncSession, user: User, intel_id: int) -> CompanyIntelOut:
    _ensure_student(user)
    row = await db.get(CompanyIntelligence, intel_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Company intelligence not found.")
    return serialize(row)


def _is_stale_generating(row: CompanyIntelligence) -> bool:
    if row.status != STATUS_GENERATING:
        return False
    ref = row.updated_at or row.created_at
    if ref is None:
        return True
    if ref.tzinfo is None:
        ref = ref.replace(tzinfo=timezone.utc)
    return datetime.now(timezone.utc) - ref > timedelta(seconds=GENERATING_STALE_SECONDS)


async def ensure_intelligence(
    db: AsyncSession,
    user: User,
    *,
    company: str,
    role: str | None = None,
    country: str | None = None,
    force_refresh: bool = False,
) -> tuple[CompanyIntelOut, bool]:
    """
    Return cached intel or start generation.
    Returns (out, started_generation).
    """
    _ensure_student(user)
    company_name = (company or "").strip()
    if not company_name:
        raise HTTPException(status_code=400, detail="company is required")
    role_name = (role or DEFAULT_ROLE).strip() or DEFAULT_ROLE
    country_name = (country or DEFAULT_COUNTRY).strip() or DEFAULT_COUNTRY

    company_key = normalize_key(company_name)
    role_key = normalize_key(role_name)
    country_key = normalize_key(country_name)
    slug = build_slug(company_name, role_name, country_name)

    row = (
        await db.execute(
            select(CompanyIntelligence).where(
                CompanyIntelligence.company_key == company_key,
                CompanyIntelligence.role_key == role_key,
                CompanyIntelligence.country_key == country_key,
            )
        )
    ).scalar_one_or_none()

    started = False
    if row is None:
        row = CompanyIntelligence(
            slug=slug,
            company_name=company_name,
            role_name=role_name,
            country=country_name,
            company_key=company_key,
            role_key=role_key,
            country_key=country_key,
            status=STATUS_GENERATING,
            prompt_version=PROMPT_VERSION,
        )
        db.add(row)
        try:
            await db.commit()
        except IntegrityError:
            await db.rollback()
            row = (
                await db.execute(
                    select(CompanyIntelligence).where(
                        CompanyIntelligence.company_key == company_key,
                        CompanyIntelligence.role_key == role_key,
                        CompanyIntelligence.country_key == country_key,
                    )
                )
            ).scalar_one()
        else:
            await db.refresh(row)
            started = True
    elif force_refresh or row.status == STATUS_FAILED or _is_stale_generating(row):
        row.status = STATUS_GENERATING
        row.error_message = None
        row.payload_json = None if force_refresh else row.payload_json
        row.updated_at = datetime.now(timezone.utc)
        await db.commit()
        await db.refresh(row)
        started = True
    elif row.status == STATUS_READY:
        started = False
    elif row.status == STATUS_GENERATING:
        started = False

    return serialize(row), started


async def run_generation(intel_id: int, llm_service: Any) -> None:
    from app.common.database.session import async_session_factory

    factory = async_session_factory()
    async with factory() as db:
        row = await db.get(CompanyIntelligence, intel_id)
        if row is None or row.status != STATUS_GENERATING:
            return
        try:
            payload, model_name = await llm_service.generate_company_intelligence(
                company=row.company_name,
                role=row.role_name,
                country=row.country,
            )
            validated = validate_company_intelligence(
                payload,
                company=row.company_name,
                role=row.role_name,
                country=row.country,
            )
            meta = validated.get("metadata") if isinstance(validated.get("metadata"), dict) else {}
            conf = meta.get("overall_confidence")
            try:
                conf_f = float(conf) if conf is not None else None
            except (TypeError, ValueError):
                conf_f = None

            row.payload_json = validated
            row.overall_confidence = conf_f
            row.evidence_strength = str(meta.get("evidence_strength") or "") or None
            row.last_updated_estimate = str(meta.get("last_updated_estimate") or "") or None
            row.model = model_name
            row.prompt_version = PROMPT_VERSION
            row.error_message = None

            if conf_f is not None and conf_f < 0.35 and not validated.get("hiring_process"):
                row.status = STATUS_UNKNOWN
            else:
                row.status = STATUS_READY
        except CompanyIntelValidationError as exc:
            logger.warning("Company intel validation failed id=%s: %s", intel_id, exc)
            row.status = STATUS_FAILED
            row.error_message = f"Incomplete intelligence payload. ({exc})"[:500]
        except Exception as exc:
            logger.exception("Company intel generation failed id=%s", intel_id)
            row.status = STATUS_FAILED
            row.error_message = (str(exc) or "Failed to generate company intelligence")[:500]

        row.completed_at = datetime.now(timezone.utc)
        await db.commit()

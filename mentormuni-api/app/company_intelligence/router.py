"""Student-facing Company Intelligence routes."""

from __future__ import annotations

from fastapi import APIRouter, BackgroundTasks, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.deps import get_db, require_api_key, require_roles
from app.company_intelligence import service as intel_service
from app.company_intelligence.schemas import (
    CompanyIntelListOut,
    CompanyIntelOut,
    EnsureCompanyIntelRequest,
)
from app.models.enums import RoleCode
from app.models.user import User
from app.services.llm import LLMService

router = APIRouter(
    prefix="/student/company-intelligence",
    tags=["Student Company Intelligence"],
    dependencies=[Depends(require_api_key)],
)

_llm = LLMService()


@router.get("", response_model=CompanyIntelListOut)
async def list_company_intelligence(
    q: str | None = Query(default=None),
    limit: int = Query(default=24, ge=1, le=50),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_roles(RoleCode.STUDENT.value)),
) -> CompanyIntelListOut:
    return await intel_service.list_intelligence(db, user, q=q, limit=limit)


@router.get("/id/{intel_id}", response_model=CompanyIntelOut)
async def get_company_intelligence_by_id(
    intel_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_roles(RoleCode.STUDENT.value)),
) -> CompanyIntelOut:
    return await intel_service.get_by_id(db, user, intel_id)


@router.get("/{slug}", response_model=CompanyIntelOut)
async def get_company_intelligence(
    slug: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_roles(RoleCode.STUDENT.value)),
) -> CompanyIntelOut:
    return await intel_service.get_by_slug(db, user, slug)


@router.post("/ensure", response_model=CompanyIntelOut)
async def ensure_company_intelligence(
    body: EnsureCompanyIntelRequest,
    background: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_roles(RoleCode.STUDENT.value)),
) -> CompanyIntelOut:
    """Return cached intel or start generation (poll GET /id/{id} while generating)."""
    out, started = await intel_service.ensure_intelligence(
        db,
        user,
        company=body.company,
        role=body.role,
        country=body.country,
        force_refresh=body.force_refresh,
    )
    if started:
        background.add_task(intel_service.run_generation, out.id, _llm)
    return out

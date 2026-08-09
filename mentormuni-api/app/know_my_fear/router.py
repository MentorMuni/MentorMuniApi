"""Student-private Know My Fear routes. Never mounted under org/TPO paths."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from app.common.deps import require_api_key, require_roles
from app.know_my_fear.schemas import FearCatalogOut, KnowMyFearRequest, KnowMyFearResponse
from app.know_my_fear.service import KnowMyFearService
from app.models.enums import RoleCode
from app.models.user import User

router = APIRouter(
    prefix="/student/know-my-fear",
    tags=["Student Know My Fear (private)"],
    dependencies=[Depends(require_api_key)],
)

_service = KnowMyFearService()


@router.get("/catalog", response_model=FearCatalogOut)
async def get_fear_catalog(
    user: User = Depends(require_roles(RoleCode.STUDENT.value)),
) -> FearCatalogOut:
    """Fear chips + privacy copy. Auth required; no org dashboards read this."""
    _ = user
    return _service.get_catalog()


@router.post("/reflect", response_model=KnowMyFearResponse)
async def reflect_on_fears(
    body: KnowMyFearRequest,
    user: User = Depends(require_roles(RoleCode.STUDENT.value)),
) -> KnowMyFearResponse:
    """
    Private reflection coach.

    Intentionally stateless: nothing is written to roadmap, assessments,
    or org performance tables — TPO/HOD cannot see this input.
    """
    return await _service.reflect(user, body)

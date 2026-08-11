"""Multi-step Fear → Fearless check-in router. Strict student-only auth."""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.deps import get_db, require_api_key, require_roles
from app.know_my_fear.intervention_service import InterventionService
from app.know_my_fear.schemas_v2 import (
    PrivateCheckInStartOut,
    PrivateCheckInStepIn,
    PrivateInsightOut,
    PrivateProgressOut,
)
from app.know_my_fear.service_v2 import FearToFearlessGateError, PrivateKnowMeService
from app.models.enums import RoleCode
from app.models.user import User

logger = logging.getLogger(__name__)

_service = PrivateKnowMeService()
_intervention = InterventionService()

TAGS = ["Fear → Fearless (private check-in)"]


def _build_router(prefix: str) -> APIRouter:
    return APIRouter(
        prefix=prefix,
        tags=TAGS,
        dependencies=[Depends(require_api_key)],
    )


router = _build_router("/student/fear-to-fearless")
legacy_router = _build_router("/student/know-me")


def _register_routes(r: APIRouter) -> None:
    @r.post("/start", response_model=PrivateCheckInStartOut)
    async def start_checkin(
        db: AsyncSession = Depends(get_db),
        user: User = Depends(require_roles(RoleCode.STUDENT.value)),
    ) -> PrivateCheckInStartOut:
        logger.info("start_checkin user_id=%s role=%s", user.id, user.role)
        try:
            result = await _service.start_checkin(db, user)
            logger.info("Check-in started: %s resumed=%s", result.checkin_id, result.resumed)
            return result
        except FearToFearlessGateError as e:
            raise HTTPException(
                status_code=409,
                detail={"code": e.code, "message": e.message, **e.payload},
            )
        except PermissionError as e:
            raise HTTPException(status_code=403, detail=str(e))
        except Exception as e:
            logger.error("start_checkin failed: %s", e, exc_info=True)
            raise HTTPException(status_code=500, detail=f"Server error: {e}")

    @r.post("/step/{checkin_id}", response_model=dict)
    async def save_step(
        checkin_id: int,
        body: PrivateCheckInStepIn,
        db: AsyncSession = Depends(get_db),
        user: User = Depends(require_roles(RoleCode.STUDENT.value)),
    ) -> dict:
        try:
            return await _service.save_step_response(db, user, checkin_id, body)
        except PermissionError as e:
            raise HTTPException(status_code=403, detail=str(e))

    @r.post("/insight/{checkin_id}", response_model=PrivateInsightOut)
    async def generate_insight(
        checkin_id: int,
        db: AsyncSession = Depends(get_db),
        user: User = Depends(require_roles(RoleCode.STUDENT.value)),
    ) -> PrivateInsightOut:
        """Generate insight, then auto-create 6-week solutions + schedule notifications."""
        try:
            insight = await _service.generate_insight(db, user, checkin_id)
            # Persist solutions so weekly journey can start immediately
            try:
                blockers = [b.model_dump() for b in (insight.blockers or [])]
                await _intervention.ensure_solutions_for_checkin(
                    db=db,
                    student=user,
                    checkin_id=checkin_id,
                    blockers=blockers,
                    responses=insight.model_dump(),
                )
            except Exception:
                logger.exception(
                    "Auto solution generation failed for checkin=%s (insight still returned)",
                    checkin_id,
                )
            await db.commit()
            return insight
        except PermissionError as e:
            raise HTTPException(status_code=403, detail=str(e))

    @r.get("/progress", response_model=PrivateProgressOut)
    async def get_progress(
        db: AsyncSession = Depends(get_db),
        user: User = Depends(require_roles(RoleCode.STUDENT.value)),
    ) -> PrivateProgressOut:
        try:
            return await _service.get_progress(db, user)
        except PermissionError as e:
            raise HTTPException(status_code=403, detail=str(e))

    @r.get("/active")
    async def get_active_journey(
        checkin_id: int | None = None,
        db: AsyncSession = Depends(get_db),
        user: User = Depends(require_roles(RoleCode.STUDENT.value)),
    ) -> dict:
        try:
            return await _service.get_active_journey(db, user, checkin_id=checkin_id)
        except PermissionError as e:
            raise HTTPException(status_code=403, detail=str(e))

    @r.get("/history")
    async def get_history(
        db: AsyncSession = Depends(get_db),
        user: User = Depends(require_roles(RoleCode.STUDENT.value)),
    ) -> dict:
        try:
            active = await _service.get_active_journey(db, user)
            return {"count": len(active.get("history") or []), "history": active.get("history") or []}
        except PermissionError as e:
            raise HTTPException(status_code=403, detail=str(e))


_register_routes(router)
_register_routes(legacy_router)

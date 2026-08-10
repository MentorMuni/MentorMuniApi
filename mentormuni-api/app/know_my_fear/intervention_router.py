"""
API routes for Fear → Fearless intervention (6-week journey).

Primary prefix: /student/fear-to-fearless
Legacy alias:   /student/know-me  (same handlers)
"""

from __future__ import annotations

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.deps import get_db, require_api_key, require_roles
from app.know_my_fear.intervention_service import InterventionService
from app.models.enums import RoleCode
from app.models.user import User

logger = logging.getLogger(__name__)

_service = InterventionService()

TAGS = ["Fear → Fearless Intervention"]


def _build_router(prefix: str) -> APIRouter:
    return APIRouter(
        prefix=prefix,
        tags=TAGS,
        dependencies=[Depends(require_api_key)],
    )


router = _build_router("/student/fear-to-fearless")
legacy_router = _build_router("/student/know-me")


class FearSolutionRequest(BaseModel):
    checkin_id: int
    fears: list[dict] = Field(default_factory=list)


class FearSolutionOut(BaseModel):
    solution_id: Optional[int] = None
    fear_name: str
    solution_data: dict


class WeeklyProgressRequest(BaseModel):
    fear_id: str
    week_number: int = Field(..., ge=1, le=6)
    actions_completed: int = Field(..., ge=0)
    actions_total: int = Field(..., ge=1)
    self_assessment: float = Field(..., ge=0, le=10)
    challenges: Optional[str] = None
    next_week_commitment: Optional[str] = None


def _register_routes(r: APIRouter) -> None:
    @r.post("/generate-solutions")
    async def generate_fear_solutions(
        req: FearSolutionRequest,
        db: AsyncSession = Depends(get_db),
        user: User = Depends(require_roles(RoleCode.STUDENT.value)),
    ) -> list[FearSolutionOut]:
        logger.info(
            "Generating solutions for student %s, checkin=%s, fears=%s",
            user.id,
            req.checkin_id,
            len(req.fears),
        )
        try:
            if req.fears:
                solutions = await _service.generate_fear_solutions(
                    db=db,
                    checkin_id=req.checkin_id,
                    student=user,
                    fears=req.fears,
                )
                await _service.schedule_6_week_notifications(
                    db=db,
                    student_id=user.id,
                    checkin_id=req.checkin_id,
                )
            else:
                solutions = await _service.ensure_solutions_for_checkin(
                    db=db,
                    student=user,
                    checkin_id=req.checkin_id,
                    blockers=[],
                )
            await db.commit()
            return [FearSolutionOut(**sol) for sol in solutions]
        except Exception as e:
            logger.error("Failed to generate solutions: %s", e, exc_info=True)
            raise HTTPException(status_code=500, detail=f"Failed to generate solutions: {e}")

    @r.post("/weekly-progress/{checkin_id}")
    async def submit_weekly_progress(
        checkin_id: int,
        req: WeeklyProgressRequest,
        db: AsyncSession = Depends(get_db),
        user: User = Depends(require_roles(RoleCode.STUDENT.value)),
    ) -> dict:
        logger.info(
            "Weekly progress student=%s fear=%s week=%s",
            user.id,
            req.fear_id,
            req.week_number,
        )
        try:
            result = await _service.submit_weekly_progress(
                db=db,
                student_id=user.id,
                checkin_id=checkin_id,
                fear_id=req.fear_id,
                week_number=req.week_number,
                actions_completed=req.actions_completed,
                actions_total=req.actions_total,
                self_assessment=req.self_assessment,
                challenges=req.challenges,
                commitment=req.next_week_commitment,
            )
            await db.commit()
            return result
        except PermissionError as e:
            raise HTTPException(status_code=403, detail=str(e))
        except Exception as e:
            logger.error("Failed to save weekly progress: %s", e, exc_info=True)
            raise HTTPException(status_code=500, detail=f"Failed to save progress: {e}")

    @r.get("/intervention-status/{checkin_id}")
    async def get_intervention_status(
        checkin_id: int,
        db: AsyncSession = Depends(get_db),
        user: User = Depends(require_roles(RoleCode.STUDENT.value)),
    ) -> dict:
        try:
            return await _service.get_intervention_status(db, user.id, checkin_id)
        except Exception as e:
            logger.error("Failed to get status: %s", e, exc_info=True)
            raise HTTPException(status_code=500, detail=f"Failed to get status: {e}")

    @r.post("/complete-intervention/{checkin_id}")
    async def complete_intervention(
        checkin_id: int,
        db: AsyncSession = Depends(get_db),
        user: User = Depends(require_roles(RoleCode.STUDENT.value)),
    ) -> dict:
        try:
            result = await _service.complete_intervention(db, user.id, checkin_id)
            await db.commit()
            return result
        except Exception as e:
            logger.error("Failed to complete intervention: %s", e, exc_info=True)
            raise HTTPException(status_code=500, detail=f"Failed to complete: {e}")

    @r.get("/notifications")
    async def list_notifications(
        unread_only: bool = False,
        db: AsyncSession = Depends(get_db),
        user: User = Depends(require_roles(RoleCode.STUDENT.value)),
    ) -> dict:
        items = await _service.list_notifications(
            db, user.id, unread_only=unread_only
        )
        return {"count": len(items), "notifications": items}

    @r.post("/notifications/{notification_id}/click")
    async def click_notification(
        notification_id: int,
        db: AsyncSession = Depends(get_db),
        user: User = Depends(require_roles(RoleCode.STUDENT.value)),
    ) -> dict:
        try:
            result = await _service.mark_notification_clicked(
                db, user.id, notification_id
            )
            await db.commit()
            return result
        except PermissionError as e:
            raise HTTPException(status_code=404, detail=str(e))


_register_routes(router)
_register_routes(legacy_router)

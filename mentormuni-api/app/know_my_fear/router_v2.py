"""Multi-step Know Me router. Strict student-only auth (no TPO/HOD access)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.deps import get_db, require_api_key, require_roles
from app.know_my_fear.schemas_v2 import (
    PrivateCheckInStartOut,
    PrivateCheckInStepIn,
    PrivateInsightOut,
    PrivateProgressOut,
)
from app.know_my_fear.service_v2 import PrivateKnowMeService
from app.models.enums import RoleCode
from app.models.user import User

router = APIRouter(
    prefix="/student/know-me",
    tags=["Student Know Me (private, student-only)"],
    dependencies=[Depends(require_api_key)],
)

_service = PrivateKnowMeService()


@router.post("/start", response_model=PrivateCheckInStartOut)
async def start_checkin(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_roles(RoleCode.STUDENT.value)),
) -> PrivateCheckInStartOut:
    """
    Start a new Know Me check-in session.
    
    Only students can use this. No TPO/HOD access (auth will reject).
    """
    try:
        return await _service.start_checkin(db, user)
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))


@router.post("/step/{checkin_id}", response_model=dict)
async def save_step(
    checkin_id: int,
    body: PrivateCheckInStepIn,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_roles(RoleCode.STUDENT.value)),
) -> dict:
    """
    Save one step response to the check-in.
    
    Strict ownership: checkin must belong to this student.
    """
    try:
        return await _service.save_step_response(db, user, checkin_id, body)
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))


@router.post("/insight/{checkin_id}", response_model=PrivateInsightOut)
async def generate_insight(
    checkin_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_roles(RoleCode.STUDENT.value)),
) -> PrivateInsightOut:
    """
    Generate elder-brother insight after check-in completion.
    
    Calls OpenAI (with heuristic fallback); stores result in private table.
    """
    try:
        return await _service.generate_insight(db, user, checkin_id)
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))


@router.get("/progress", response_model=PrivateProgressOut)
async def get_progress(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_roles(RoleCode.STUDENT.value)),
) -> PrivateProgressOut:
    """
    Compare first and latest check-ins for 30–45 day growth.
    """
    try:
        return await _service.get_progress(db, user)
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))

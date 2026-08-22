"""Student 24/7 personal VOICE mentor routes (OpenAI Realtime)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.deps import get_db, require_api_key, require_roles
from app.common.rate_limit import limiter
from app.models.enums import RoleCode
from app.models.user import User
from app.personal_mentor.schemas import (
    MentorContextOut,
    MentorVoiceSessionRequest,
    MentorVoiceSessionResponse,
)
from app.personal_mentor.service import PersonalMentorService

router = APIRouter(
    prefix="/student/mentor",
    tags=["Student Personal Mentor"],
    dependencies=[Depends(require_api_key)],
)

_service = PersonalMentorService()


@router.get("/context", response_model=MentorContextOut)
async def get_mentor_context(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_roles(RoleCode.STUDENT.value)),
) -> MentorContextOut:
    """Snapshot of this student's scores/plan for the mentor UI chips."""
    return await _service.get_context(db, user)


@router.post("/voice/session", response_model=MentorVoiceSessionResponse)
@limiter.limit("100/minute")
async def create_mentor_voice_session(
    request: Request,
    body: MentorVoiceSessionRequest | None = None,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_roles(RoleCode.STUDENT.value)),
) -> MentorVoiceSessionResponse:
    """Mint OpenAI Realtime ephemeral key for the 24/7 voice mentor WebRTC call."""
    req = body or MentorVoiceSessionRequest()
    return await _service.create_voice_session(db, user, voice=req.voice)

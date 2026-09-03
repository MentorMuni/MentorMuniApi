"""Student Aptitude Arcade routes — AI question packs."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from app.aptitude_arcade.schemas import ArcadeGenerateIn, ArcadeGenerateOut
from app.aptitude_arcade.service import AptitudeArcadeService, ArcadeError
from app.common.deps import require_api_key, require_roles
from app.models.enums import RoleCode
from app.models.user import User

router = APIRouter(
    prefix="/student/aptitude-arcade",
    tags=["Student Aptitude Arcade"],
    dependencies=[Depends(require_api_key)],
)

_service = AptitudeArcadeService()


def _http(exc: ArcadeError) -> HTTPException:
    return HTTPException(status_code=exc.status_code, detail=exc.message)


@router.post("/generate", response_model=ArcadeGenerateOut)
async def generate_questions(
    body: ArcadeGenerateIn,
    user: User = Depends(require_roles(RoleCode.STUDENT.value)),
) -> ArcadeGenerateOut:
    """Replace the current pack: OpenAI generates a fresh set of questions for one game."""
    _ = user  # auth gate only — packs are ephemeral client-side
    try:
        return await _service.generate(game_id=body.game_id, count=body.count)
    except ArcadeError as exc:
        raise _http(exc) from exc

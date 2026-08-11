"""Student White Board routes — notes plus on-open morning mentorship."""

from __future__ import annotations

from datetime import date

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.deps import get_db, require_api_key, require_roles
from app.models.enums import RoleCode
from app.models.user import User
from app.whiteboard.schemas import BoardOut, MentorshipOut, NoteCreateIn, NoteOut, NoteUpdateIn
from app.whiteboard.service import WhiteboardError, WhiteboardService

router = APIRouter(
    prefix="/student/whiteboard",
    tags=["Student White Board"],
    dependencies=[Depends(require_api_key)],
)

_service = WhiteboardService()


def _http(exc: WhiteboardError) -> HTTPException:
    return HTTPException(status_code=exc.status_code, detail=exc.message)


def _kickoff(background: BackgroundTasks, mentorship_id: int | None) -> None:
    if mentorship_id is not None:
        background.add_task(_service.run_morning_generation, mentorship_id)


@router.get("", response_model=BoardOut)
async def get_board(
    background: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_roles(RoleCode.STUDENT.value)),
) -> BoardOut:
    """Wall + today's drop. Generates yesterday→today mentorship once per IST day on first open."""
    try:
        board, generate_id = await _service.get_board(db, user)
    except WhiteboardError as exc:
        raise _http(exc) from exc
    _kickoff(background, generate_id)
    return board


@router.post("/morning", response_model=BoardOut)
async def ensure_morning(
    background: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_roles(RoleCode.STUDENT.value)),
) -> BoardOut:
    """Portal-open hook. Same as GET — one OpenAI call per student per campus day, no cron."""
    try:
        board, generate_id = await _service.get_board(db, user)
    except WhiteboardError as exc:
        raise _http(exc) from exc
    _kickoff(background, generate_id)
    return board


@router.post("/notes", response_model=NoteOut, status_code=201)
async def create_note(
    body: NoteCreateIn,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_roles(RoleCode.STUDENT.value)),
) -> NoteOut:
    try:
        return await _service.create_note(db, user, body)
    except WhiteboardError as exc:
        raise _http(exc) from exc


@router.patch("/notes/{note_id}", response_model=NoteOut)
async def update_note(
    note_id: int,
    body: NoteUpdateIn,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_roles(RoleCode.STUDENT.value)),
) -> NoteOut:
    try:
        return await _service.update_note(db, user, note_id, body)
    except WhiteboardError as exc:
        raise _http(exc) from exc


@router.post("/notes/{note_id}/resolve", response_model=NoteOut)
async def resolve_note(
    note_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_roles(RoleCode.STUDENT.value)),
) -> NoteOut:
    try:
        return await _service.resolve_note(db, user, note_id)
    except WhiteboardError as exc:
        raise _http(exc) from exc


@router.post("/notes/{note_id}/reopen", response_model=NoteOut)
async def reopen_note(
    note_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_roles(RoleCode.STUDENT.value)),
) -> NoteOut:
    try:
        return await _service.reopen_note(db, user, note_id)
    except WhiteboardError as exc:
        raise _http(exc) from exc


@router.get("/mentorships/{mentorship_date}", response_model=MentorshipOut)
async def get_mentorship(
    mentorship_date: date,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_roles(RoleCode.STUDENT.value)),
) -> MentorshipOut:
    try:
        return await _service.get_mentorship(db, user, mentorship_date)
    except WhiteboardError as exc:
        raise _http(exc) from exc

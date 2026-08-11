"""White Board business logic: notes + one IST-day mentorship, no cron."""

from __future__ import annotations

import json
import logging
from datetime import date, datetime, timedelta, timezone
from typing import Any, Optional
from zoneinfo import ZoneInfo

from openai import AsyncOpenAI
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import settings
from app.models.enums import RoleCode
from app.models.user import User
from app.models.whiteboard import (
    MENTORSHIP_GENERATING,
    MENTORSHIP_READY,
    NOTE_STATUS_OPEN,
    NOTE_STATUS_RESOLVED,
    WhiteboardMentorship,
    WhiteboardNote,
)
from app.whiteboard.prompt import WHITEBOARD_MENTOR_SYSTEM, build_mentorship_user_prompt
from app.whiteboard.schemas import (
    NOTE_COLORS,
    BoardOut,
    MentorshipActionOut,
    MentorshipListItemOut,
    MentorshipOut,
    NoteCreateIn,
    NoteOut,
    NoteUpdateIn,
)

logger = logging.getLogger(__name__)

CAMPUS_TZ = ZoneInfo("Asia/Kolkata")
GENERATING_STALE_SECONDS = 120
MAX_OPEN_NOTES = 60
NOTE_HISTORY_DAYS = 45
MENTORSHIP_HISTORY_DAYS = 45
RESOLVED_CONTEXT_DAYS = 14

NOTE_COLORS_CYCLE = list(NOTE_COLORS)


class WhiteboardError(Exception):
    def __init__(self, status_code: int, message: str):
        super().__init__(message)
        self.status_code = status_code
        self.message = message


def campus_today() -> date:
    return datetime.now(CAMPUS_TZ).date()


def campus_yesterday(today: Optional[date] = None) -> date:
    return (today or campus_today()) - timedelta(days=1)


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _require_student(user: User) -> None:
    code = user.role.role_code if user.role else None
    if code != RoleCode.STUDENT.value:
        raise WhiteboardError(403, "Only students can use the White Board.")


def _color(raw: Optional[str], fallback: str = "canary") -> str:
    value = (raw or fallback).strip().lower()
    return value if value in NOTE_COLORS else fallback


def _next_pin(open_count: int) -> tuple[float, float, float]:
    cols = 4
    col = open_count % cols
    row = open_count // cols
    jitter_x = ((open_count * 17) % 7) - 3
    jitter_y = ((open_count * 13) % 7) - 3
    pin_x = max(2.0, min(78.0, 5.0 + col * 23.0 + jitter_x))
    pin_y = max(2.0, min(72.0, 6.0 + row * 26.0 + jitter_y))
    rotation = float(((open_count * 11) % 15) - 7)
    return pin_x, pin_y, rotation


def _note_out(row: WhiteboardNote) -> NoteOut:
    return NoteOut(
        id=row.id,
        body=row.body,
        color=row.color,
        status=row.status,
        board_date=row.board_date,
        pin_x=row.pin_x,
        pin_y=row.pin_y,
        rotation=row.rotation,
        created_at=row.created_at,
        updated_at=row.updated_at,
        resolved_at=row.resolved_at,
    )


def _actions_from_json(raw: Any) -> list[MentorshipActionOut]:
    items: list[MentorshipActionOut] = []
    if not isinstance(raw, list):
        return items
    for i, item in enumerate(raw, 1):
        if not isinstance(item, dict):
            continue
        note_ids: list[int] = []
        for nid in item.get("note_ids") or []:
            try:
                note_ids.append(int(nid))
            except (TypeError, ValueError):
                continue
        minutes = item.get("timebox_minutes") or 25
        try:
            minutes = int(minutes)
        except (TypeError, ValueError):
            minutes = 25
        minutes = max(10, min(90, minutes))
        items.append(
            MentorshipActionOut(
                order=int(item.get("order") or i),
                title=str(item.get("title") or f"Move {i}").strip()[:80],
                do_exactly=str(item.get("do_exactly") or "").strip()[:800],
                why_this_works=str(item.get("why_this_works") or "").strip()[:400],
                done_when=str(item.get("done_when") or "").strip()[:400],
                timebox_minutes=minutes,
                note_ids=note_ids[:8],
            )
        )
    return items[:4]


def _mentorship_out(row: WhiteboardMentorship) -> MentorshipOut:
    return MentorshipOut(
        id=row.id,
        mentorship_date=row.mentorship_date,
        source_notes_date=row.source_notes_date,
        status=row.status,
        headline=row.headline or "",
        greeting=row.greeting or "",
        what_changed=row.what_changed or "",
        diagnosis=row.diagnosis or "",
        actions=_actions_from_json(row.actions_json),
        callout=row.callout or "",
        closing=row.closing or "",
        source=row.source or "heuristic",
        model=row.model,
    )


def _is_stale(row: WhiteboardMentorship) -> bool:
    if row.status != MENTORSHIP_GENERATING:
        return False
    started = row.updated_at or row.created_at
    if started is None:
        return True
    if started.tzinfo is None:
        started = started.replace(tzinfo=timezone.utc)
    return (utc_now() - started).total_seconds() > GENERATING_STALE_SECONDS


def _note_payload(row: WhiteboardNote) -> dict[str, Any]:
    resolved = None
    if row.resolved_at is not None:
        resolved = row.resolved_at.isoformat()
    return {
        "id": row.id,
        "body": row.body,
        "status": row.status,
        "board_date": row.board_date.isoformat(),
        "resolved_at": resolved,
    }


def _empty_payload(first_name: str) -> dict[str, Any]:
    name = first_name or "hey"
    return {
        "headline": "Wall is quiet. Dump the real mess tonight.",
        "greeting": f"{name}, I opened your board. Nothing from yesterday to fix yet.",
        "what_changed": "No new notes yesterday, and nothing leftover is screaming. That is either peace or avoidance — you will know which.",
        "diagnosis": "A blank wall cannot be coached. Write the thing you are actually stuck on: the subject, the company, the hour you froze, what you want by Friday. Vague notes get vague lives.",
        "actions": [
            {
                "order": 1,
                "title": "Slap one honest note",
                "do_exactly": "Write one sticky in 2 minutes: the problem in one sentence + what 'fixed' looks like by tonight. Example: 'Arrays freeze me — I want 2 easy problems submitted without watching a video.'",
                "why_this_works": "Tomorrow's drop can only be exact if tonight's note is exact.",
                "done_when": "One open sticky is on the wall with a finish line, not a vibe.",
                "timebox_minutes": 10,
                "note_ids": [],
            }
        ],
        "callout": "If you only do one thing: put the real blocker on the wall before you sleep.",
        "closing": "I will be here tomorrow morning. Peel nothing that is not actually done.",
    }


def _heuristic_payload(
    first_name: str,
    yesterday_notes: list[WhiteboardNote],
    open_older: list[WhiteboardNote],
    resolved: list[WhiteboardNote],
) -> dict[str, Any]:
    name = first_name or "hey"
    focus = yesterday_notes or open_older
    peeled = f"You peeled {len(resolved)} note(s). Good — I will not reopen those." if resolved else "Nothing peeled recently."
    if not focus:
        return _empty_payload(first_name)

    actions: list[dict[str, Any]] = []
    for i, note in enumerate(focus[:4], 1):
        snippet = (note.body or "").strip().replace("\n", " ")
        short = snippet if len(snippet) <= 90 else snippet[:87] + "…"
        actions.append(
            {
                "order": i,
                "title": f"Close this: {short[:42]}",
                "do_exactly": (
                    f"Set a 25-minute timer. Phone in another room. Write the problem '{short}' "
                    "at the top of a page. Spend 10 minutes listing what you already tried. "
                    "Spend 15 minutes doing the smallest next artefact: one problem submitted, "
                    "one paragraph rewritten, one mock answer spoken out loud, or one email sent. "
                    "No YouTube until the artefact exists."
                ),
                "why_this_works": "You named this on the wall. The freeze is usually starting, not talent.",
                "done_when": f"You can show a screenshot/file/message that proves '{short}' moved, then peel note #{note.id}.",
                "timebox_minutes": 25,
                "note_ids": [note.id],
            }
        )

    lead = (focus[0].body or "").strip().replace("\n", " ")
    lead_short = lead if len(lead) <= 80 else lead[:77] + "…"
    leftover = (
        f" Plus {len(open_older)} older note(s) still stuck to the wall."
        if open_older and yesterday_notes
        else ""
    )
    return {
        "headline": f"Today we kill this: {lead_short}",
        "greeting": f"{name}, I read yesterday's stickies. We are not hoping. We are closing them.",
        "what_changed": f"{peeled}{leftover}",
        "diagnosis": (
            "The pattern is usually the same: the note is a fog ('I am bad at X') instead of a move. "
            "Today you turn each fog into one timed artefact. If you finish the artefact, peel the note. "
            "If you do not, the note stays. That is the contract."
        ),
        "actions": actions,
        "callout": f"If you only do one thing, finish action 1 on: {lead_short}",
        "closing": "Peel only when the done-when is true. I will see what is left tomorrow.",
    }


def _parse_model_json(content: str, fallback: dict[str, Any]) -> dict[str, Any]:
    try:
        data = json.loads(content)
    except json.JSONDecodeError:
        return fallback
    if not isinstance(data, dict):
        return fallback
    actions = _actions_from_json(data.get("actions"))
    if not actions:
        return fallback
    return {
        "headline": str(data.get("headline") or fallback["headline"]).strip()[:180],
        "greeting": str(data.get("greeting") or fallback["greeting"]).strip()[:280],
        "what_changed": str(data.get("what_changed") or fallback["what_changed"]).strip()[:600],
        "diagnosis": str(data.get("diagnosis") or fallback["diagnosis"]).strip()[:1200],
        "actions": [a.model_dump() for a in actions],
        "callout": str(data.get("callout") or fallback["callout"]).strip()[:400],
        "closing": str(data.get("closing") or fallback["closing"]).strip()[:280],
    }


class WhiteboardService:
    async def get_board(self, db: AsyncSession, user: User) -> tuple[BoardOut, Optional[int]]:
        """Return the wall. Second value is a mentorship id to generate in the background."""
        _require_student(user)
        today = campus_today()
        yesterday = campus_yesterday(today)
        notes = await self._load_notes(db, user.id)
        history = await self._load_mentorship_history(db, user.id, today)
        today_row, generate_id = await self._claim_today(db, user, today, yesterday, notes)
        return (
            self._to_board(today, yesterday, notes, history, today_row),
            generate_id,
        )

    async def create_note(self, db: AsyncSession, user: User, body: NoteCreateIn) -> NoteOut:
        _require_student(user)
        text = (body.body or "").strip()
        if not text:
            raise WhiteboardError(400, "Write something on the note first.")
        open_rows = await db.execute(
            select(WhiteboardNote).where(
                WhiteboardNote.student_id == user.id,
                WhiteboardNote.status == NOTE_STATUS_OPEN,
            )
        )
        open_list = list(open_rows.scalars().all())
        if len(open_list) >= MAX_OPEN_NOTES:
            raise WhiteboardError(400, "Peel a few solved notes before adding more — 60 is the wall's limit.")

        pin_x, pin_y, rotation = _next_pin(len(open_list))
        if body.pin_x is not None:
            pin_x = body.pin_x
        if body.pin_y is not None:
            pin_y = body.pin_y
        if body.rotation is not None:
            rotation = body.rotation

        color = _color(body.color, NOTE_COLORS_CYCLE[len(open_list) % len(NOTE_COLORS_CYCLE)])
        row = WhiteboardNote(
            student_id=user.id,
            organization_id=user.organization_id,
            body=text,
            color=color,
            status=NOTE_STATUS_OPEN,
            board_date=campus_today(),
            pin_x=pin_x,
            pin_y=pin_y,
            rotation=rotation,
        )
        db.add(row)
        await db.flush()
        await db.refresh(row)
        return _note_out(row)

    async def update_note(self, db: AsyncSession, user: User, note_id: int, body: NoteUpdateIn) -> NoteOut:
        _require_student(user)
        row = await self._owned_note(db, user.id, note_id)
        if body.body is not None:
            text = body.body.strip()
            if not text:
                raise WhiteboardError(400, "Note cannot be empty.")
            row.body = text
        if body.color is not None:
            row.color = _color(body.color, row.color)
        if body.pin_x is not None:
            row.pin_x = body.pin_x
        if body.pin_y is not None:
            row.pin_y = body.pin_y
        if body.rotation is not None:
            row.rotation = body.rotation
        row.updated_at = utc_now()
        await db.flush()
        await db.refresh(row)
        return _note_out(row)

    async def resolve_note(self, db: AsyncSession, user: User, note_id: int) -> NoteOut:
        _require_student(user)
        row = await self._owned_note(db, user.id, note_id)
        if row.status != NOTE_STATUS_RESOLVED:
            row.status = NOTE_STATUS_RESOLVED
            row.resolved_at = utc_now()
            row.updated_at = utc_now()
            await db.flush()
            await db.refresh(row)
        return _note_out(row)

    async def reopen_note(self, db: AsyncSession, user: User, note_id: int) -> NoteOut:
        _require_student(user)
        row = await self._owned_note(db, user.id, note_id)
        if row.status != NOTE_STATUS_OPEN:
            open_count = await self._open_count(db, user.id)
            if open_count >= MAX_OPEN_NOTES:
                raise WhiteboardError(400, "Peel a solved note before putting this one back.")
            row.status = NOTE_STATUS_OPEN
            row.resolved_at = None
            row.updated_at = utc_now()
            await db.flush()
            await db.refresh(row)
        return _note_out(row)

    async def get_mentorship(self, db: AsyncSession, user: User, mentorship_date: date) -> MentorshipOut:
        _require_student(user)
        row = (
            await db.execute(
                select(WhiteboardMentorship).where(
                    WhiteboardMentorship.student_id == user.id,
                    WhiteboardMentorship.mentorship_date == mentorship_date,
                )
            )
        ).scalar_one_or_none()
        if row is None:
            raise WhiteboardError(404, "No mentorship for that date yet.")
        return _mentorship_out(row)

    async def run_morning_generation(self, mentorship_id: int) -> None:
        from app.common.database.session import async_session_factory

        factory = async_session_factory()
        async with factory() as db:
            row = await db.get(WhiteboardMentorship, mentorship_id)
            if row is None or row.status != MENTORSHIP_GENERATING:
                return
            try:
                await self._fill_mentorship(db, row)
                await db.commit()
            except Exception:
                logger.exception("White Board mentorship generation failed id=%s", mentorship_id)
                await db.rollback()
                row = await db.get(WhiteboardMentorship, mentorship_id)
                if row is None:
                    return
                try:
                    user = await db.get(User, row.student_id)
                    notes = await self._load_notes(db, row.student_id)
                    today = row.mentorship_date
                    yesterday = row.source_notes_date
                    y_notes = [n for n in notes if n.board_date == yesterday]
                    open_older = [
                        n
                        for n in notes
                        if n.status == NOTE_STATUS_OPEN and n.board_date < yesterday
                    ]
                    resolved = [
                        n
                        for n in notes
                        if n.status == NOTE_STATUS_RESOLVED
                        and n.resolved_at is not None
                        and n.resolved_at.date() >= (today - timedelta(days=RESOLVED_CONTEXT_DAYS))
                    ]
                    payload = _heuristic_payload(
                        user.first_name if user else "hey",
                        y_notes,
                        open_older,
                        resolved,
                    )
                    self._apply_payload(row, payload, source="heuristic", model=None)
                    await db.commit()
                except Exception:
                    logger.exception("White Board heuristic fallback also failed id=%s", mentorship_id)
                    await db.rollback()

    async def _fill_mentorship(self, db: AsyncSession, row: WhiteboardMentorship) -> None:
        user = (
            await db.execute(
                select(User)
                .options(selectinload(User.organization), selectinload(User.department))
                .where(User.id == row.student_id)
            )
        ).scalar_one_or_none()
        if user is None:
            raise RuntimeError("student missing")
        notes = await self._load_notes(db, row.student_id)
        today = row.mentorship_date
        yesterday = row.source_notes_date
        y_notes = [n for n in notes if n.board_date == yesterday]
        open_older = [n for n in notes if n.status == NOTE_STATUS_OPEN and n.board_date < yesterday]
        resolved = [
            n
            for n in notes
            if n.status == NOTE_STATUS_RESOLVED
            and n.resolved_at is not None
            and (n.resolved_at.astimezone(CAMPUS_TZ).date() if n.resolved_at.tzinfo else n.resolved_at.date())
            >= (today - timedelta(days=RESOLVED_CONTEXT_DAYS))
        ]
        previous = (
            await db.execute(
                select(WhiteboardMentorship)
                .where(
                    WhiteboardMentorship.student_id == row.student_id,
                    WhiteboardMentorship.mentorship_date < today,
                    WhiteboardMentorship.status == MENTORSHIP_READY,
                )
                .order_by(WhiteboardMentorship.mentorship_date.desc())
                .limit(1)
            )
        ).scalar_one_or_none()

        first_name = (user.first_name or "hey").strip()
        college = user.organization.name if user.organization else None
        department = user.department.name if getattr(user, "department", None) else None
        fallback = _heuristic_payload(first_name, y_notes, open_older, resolved)

        if not y_notes and not open_older:
            self._apply_payload(row, _empty_payload(first_name), source="empty", model=None)
            return

        payload = fallback
        source = "heuristic"
        model = None
        api_key = (settings.openai_api_key or "").strip()
        if api_key:
            model = settings.whiteboard_model
            prev_dict = None
            if previous is not None:
                prev_dict = {
                    "mentorship_date": previous.mentorship_date.isoformat(),
                    "headline": previous.headline,
                    "diagnosis": previous.diagnosis,
                    "actions": previous.actions_json or [],
                }
            user_prompt = build_mentorship_user_prompt(
                first_name=first_name,
                college=college,
                department=department,
                today=today.isoformat(),
                yesterday=yesterday.isoformat(),
                yesterday_notes=[_note_payload(n) for n in y_notes],
                open_older_notes=[_note_payload(n) for n in open_older],
                recently_resolved=[_note_payload(n) for n in resolved[:20]],
                previous_mentorship=prev_dict,
            )
            try:
                client = AsyncOpenAI(api_key=api_key)
                resp = await client.chat.completions.create(
                    model=model,
                    messages=[
                        {"role": "system", "content": WHITEBOARD_MENTOR_SYSTEM},
                        {"role": "user", "content": user_prompt},
                    ],
                    temperature=0.55,
                    max_tokens=1800,
                    response_format={"type": "json_object"},
                )
                content = (resp.choices[0].message.content or "").strip()
                payload = _parse_model_json(content, fallback)
                source = "openai"
            except Exception:
                logger.exception("White Board OpenAI call failed; using heuristic")
                payload = fallback
                source = "heuristic"
                model = None

        self._apply_payload(row, payload, source=source, model=model)

    def _apply_payload(
        self,
        row: WhiteboardMentorship,
        payload: dict[str, Any],
        *,
        source: str,
        model: Optional[str],
    ) -> None:
        row.headline = str(payload.get("headline") or "")
        row.greeting = str(payload.get("greeting") or "")
        row.what_changed = str(payload.get("what_changed") or "")
        row.diagnosis = str(payload.get("diagnosis") or "")
        row.actions_json = payload.get("actions") or []
        row.callout = str(payload.get("callout") or "")
        row.closing = str(payload.get("closing") or "")
        row.source = source
        row.model = model
        row.raw_json = payload
        row.status = MENTORSHIP_READY
        row.updated_at = utc_now()

    async def _claim_today(
        self,
        db: AsyncSession,
        user: User,
        today: date,
        yesterday: date,
        notes: list[WhiteboardNote],
    ) -> tuple[Optional[WhiteboardMentorship], Optional[int]]:
        existing = (
            await db.execute(
                select(WhiteboardMentorship).where(
                    WhiteboardMentorship.student_id == user.id,
                    WhiteboardMentorship.mentorship_date == today,
                )
            )
        ).scalar_one_or_none()

        if existing is not None and existing.status == MENTORSHIP_READY:
            return existing, None

        if existing is not None and existing.status == MENTORSHIP_GENERATING:
            if not _is_stale(existing):
                return existing, None
            existing.updated_at = utc_now()
            await db.flush()
            return existing, existing.id

        y_notes = [n for n in notes if n.board_date == yesterday]
        open_older = [n for n in notes if n.status == NOTE_STATUS_OPEN and n.board_date < yesterday]
        if not y_notes and not open_older:
            payload = _empty_payload(user.first_name or "hey")
            stmt = (
                insert(WhiteboardMentorship)
                .values(
                    student_id=user.id,
                    organization_id=user.organization_id,
                    mentorship_date=today,
                    source_notes_date=yesterday,
                    status=MENTORSHIP_READY,
                    headline=payload["headline"],
                    greeting=payload["greeting"],
                    what_changed=payload["what_changed"],
                    diagnosis=payload["diagnosis"],
                    actions_json=payload["actions"],
                    callout=payload["callout"],
                    closing=payload["closing"],
                    source="empty",
                    raw_json=payload,
                )
                .on_conflict_do_nothing(constraint="uq_whiteboard_mentorship_student_date")
            )
            await db.execute(stmt)
            await db.flush()
            return await self._today_row(db, user.id, today), None

        stmt = (
            insert(WhiteboardMentorship)
            .values(
                student_id=user.id,
                organization_id=user.organization_id,
                mentorship_date=today,
                source_notes_date=yesterday,
                status=MENTORSHIP_GENERATING,
                headline="",
                greeting="",
                what_changed="",
                diagnosis="",
                actions_json=[],
                callout="",
                closing="",
                source="openai",
            )
            .on_conflict_do_nothing(constraint="uq_whiteboard_mentorship_student_date")
            .returning(WhiteboardMentorship.id)
        )
        inserted_id = (await db.execute(stmt)).scalar_one_or_none()
        await db.flush()
        row = await self._today_row(db, user.id, today)
        if row is None:
            return None, None
        if row.status == MENTORSHIP_READY:
            return row, None
        if inserted_id:
            return row, row.id
        if _is_stale(row):
            row.updated_at = utc_now()
            await db.flush()
            return row, row.id
        return row, None

    async def _today_row(
        self, db: AsyncSession, student_id: int, today: date
    ) -> Optional[WhiteboardMentorship]:
        return (
            await db.execute(
                select(WhiteboardMentorship).where(
                    WhiteboardMentorship.student_id == student_id,
                    WhiteboardMentorship.mentorship_date == today,
                )
            )
        ).scalar_one_or_none()

    def _to_board(
        self,
        today: date,
        yesterday: date,
        notes: list[WhiteboardNote],
        history: list[WhiteboardMentorship],
        today_row: Optional[WhiteboardMentorship],
    ) -> BoardOut:
        generating = bool(today_row is not None and today_row.status == MENTORSHIP_GENERATING)
        today_out = None
        if today_row is not None and today_row.status == MENTORSHIP_READY:
            today_out = _mentorship_out(today_row)
        return BoardOut(
            today=today,
            yesterday=yesterday,
            timezone="Asia/Kolkata",
            generating=generating,
            notes=[_note_out(n) for n in notes],
            today_mentorship=today_out,
            mentorships=[
                MentorshipListItemOut(
                    id=m.id,
                    mentorship_date=m.mentorship_date,
                    status=m.status,
                    headline=m.headline or "Morning drop",
                    source=m.source,
                )
                for m in history
            ],
            yesterday_note_count=sum(1 for n in notes if n.board_date == yesterday),
            open_note_count=sum(1 for n in notes if n.status == NOTE_STATUS_OPEN),
        )

    async def _load_notes(self, db: AsyncSession, student_id: int) -> list[WhiteboardNote]:
        cutoff = campus_today() - timedelta(days=NOTE_HISTORY_DAYS)
        rows = await db.execute(
            select(WhiteboardNote)
            .where(
                WhiteboardNote.student_id == student_id,
                (WhiteboardNote.status == NOTE_STATUS_OPEN) | (WhiteboardNote.board_date >= cutoff),
            )
            .order_by(WhiteboardNote.created_at.asc())
        )
        return list(rows.scalars().all())

    async def _load_mentorship_history(
        self, db: AsyncSession, student_id: int, today: date
    ) -> list[WhiteboardMentorship]:
        cutoff = today - timedelta(days=MENTORSHIP_HISTORY_DAYS)
        rows = await db.execute(
            select(WhiteboardMentorship)
            .where(
                WhiteboardMentorship.student_id == student_id,
                WhiteboardMentorship.mentorship_date >= cutoff,
            )
            .order_by(WhiteboardMentorship.mentorship_date.desc())
        )
        return list(rows.scalars().all())

    async def _owned_note(self, db: AsyncSession, student_id: int, note_id: int) -> WhiteboardNote:
        row = await db.get(WhiteboardNote, note_id)
        if row is None or row.student_id != student_id:
            raise WhiteboardError(404, "That sticky is not on your wall.")
        return row

    async def _open_count(self, db: AsyncSession, student_id: int) -> int:
        rows = await db.execute(
            select(WhiteboardNote.id).where(
                WhiteboardNote.student_id == student_id,
                WhiteboardNote.status == NOTE_STATUS_OPEN,
            )
        )
        return len(list(rows.scalars().all()))

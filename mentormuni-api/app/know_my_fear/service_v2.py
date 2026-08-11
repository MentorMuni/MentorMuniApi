"""Core service: multi-step Know Me flow + private auth enforcement."""

from __future__ import annotations

import json
import logging
from datetime import datetime, timedelta
from typing import Any, Optional

from openai import AsyncOpenAI
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.config import settings
from app.know_my_fear.constants import PLAN_LOCK_DAYS
from app.know_my_fear.insight_prompt import KNOW_ME_INSIGHT_SYSTEM, build_insight_user_prompt
from app.know_my_fear.intervention_service import InterventionService
from app.know_my_fear.questions import KNOW_ME_QUESTIONS, get_question_by_key, question_keys
from app.know_my_fear.schemas_v2 import (
    ActionItem,
    BlockerItem,
    PrivateCheckInStartOut,
    PrivateCheckInStepIn,
    PrivateInsightOut,
    PrivateProgressOut,
)
from app.know_my_fear.timeutil import utc_now
from app.models.enums import RoleCode
from app.models.private_checkin import (
    PrivateStudentCheckIn,
    PrivateStudentInsight,
    PrivateStudentResponse,
    PrivateStudentProgress,
)
from app.models.private_intervention import PrivateStudentFearSolution
from app.models.user import User

logger = logging.getLogger(__name__)

_intervention = InterventionService()


class FearToFearlessGateError(Exception):
    """Student cannot start a new check-in (locked or must resume)."""

    def __init__(self, code: str, message: str, payload: Optional[dict] = None):
        super().__init__(message)
        self.code = code
        self.message = message
        self.payload = payload or {}


def _require_student(user: User, action: str = "use Fear → Fearless") -> None:
    """user.role is a Role relationship, not a string — compare role_code."""
    code = user.role.role_code if user.role else None
    if code != RoleCode.STUDENT.value:
        raise PermissionError(f"Only students can {action}.")


def _as_naive(dt: Optional[datetime]) -> Optional[datetime]:
    if dt is None:
        return None
    if dt.tzinfo is not None:
        return dt.replace(tzinfo=None)
    return dt


def _lock_window(anchor: Optional[datetime]) -> dict[str, Any]:
    start = _as_naive(anchor)
    if not start:
        return {
            "locked": False,
            "unlocks_at": None,
            "days_remaining": 0,
            "days_elapsed": 0,
            "can_start": True,
        }
    unlocks = start + timedelta(days=PLAN_LOCK_DAYS)
    now = utc_now()
    locked = now < unlocks
    remaining = max(0, (unlocks.date() - now.date()).days) if locked else 0
    elapsed = max(0, (now.date() - start.date()).days)
    return {
        "locked": locked,
        "unlocks_at": unlocks.isoformat(),
        "days_remaining": remaining if locked else 0,
        "days_elapsed": min(PLAN_LOCK_DAYS, elapsed),
        "can_start": not locked,
    }


class PrivateKnowMeService:
    """Multi-step Know Me flow. Private to student; never org-visible."""

    async def _latest_checkin(
        self, db: AsyncSession, student_id: int
    ) -> Optional[PrivateStudentCheckIn]:
        return (
            await db.execute(
                select(PrivateStudentCheckIn)
                .where(PrivateStudentCheckIn.student_id == student_id)
                .order_by(PrivateStudentCheckIn.created_at.desc())
                .limit(1)
            )
        ).scalar_one_or_none()

    async def _plan_anchor(
        self, db: AsyncSession, checkin: PrivateStudentCheckIn
    ) -> Optional[datetime]:
        if checkin.completed_at:
            return _as_naive(checkin.completed_at)
        insight = (
            await db.execute(
                select(PrivateStudentInsight)
                .where(PrivateStudentInsight.checkin_id == checkin.id)
                .order_by(PrivateStudentInsight.created_at.desc())
                .limit(1)
            )
        ).scalar_one_or_none()
        if insight and insight.created_at:
            return _as_naive(insight.created_at)
        sol = (
            await db.execute(
                select(PrivateStudentFearSolution)
                .where(PrivateStudentFearSolution.checkin_id == checkin.id)
                .order_by(PrivateStudentFearSolution.created_at.asc())
                .limit(1)
            )
        ).scalar_one_or_none()
        if sol and sol.created_at:
            return _as_naive(sol.created_at)
        return None

    async def _has_plan(self, db: AsyncSession, checkin_id: int) -> bool:
        insight = (
            await db.execute(
                select(PrivateStudentInsight.id)
                .where(PrivateStudentInsight.checkin_id == checkin_id)
                .limit(1)
            )
        ).scalar()
        if insight:
            return True
        sol = (
            await db.execute(
                select(PrivateStudentFearSolution.id)
                .where(PrivateStudentFearSolution.checkin_id == checkin_id)
                .limit(1)
            )
        ).scalar()
        return bool(sol)

    async def _saved_responses(
        self, db: AsyncSession, checkin_id: int
    ) -> list[dict[str, Any]]:
        rows = list(
            (
                await db.execute(
                    select(PrivateStudentResponse)
                    .where(PrivateStudentResponse.checkin_id == checkin_id)
                    .order_by(PrivateStudentResponse.created_at.asc())
                )
            ).scalars().all()
        )
        latest: dict[str, dict[str, Any]] = {}
        for row in rows:
            val = row.response_value if isinstance(row.response_value, dict) else {}
            latest[row.question_key] = {
                "question_key": row.question_key,
                "selected_ids": list(val.get("selected_ids") or []),
                "free_text": val.get("free_text") or "",
            }
        return list(latest.values())

    def _step_index_from_saved(self, saved: list[dict[str, Any]]) -> int:
        answered = {r["question_key"] for r in saved}
        keys = question_keys()
        for i, key in enumerate(keys):
            if key not in answered:
                return i
        return max(0, len(keys) - 1)

    async def start_checkin(
        self, db: AsyncSession, user: User
    ) -> PrivateCheckInStartOut:
        """Create a new check-in, or resume / reject when a plan is still locked."""
        _require_student(user, "use Fear → Fearless")

        latest = await self._latest_checkin(db, user.id)
        questions = [q.model_dump() for q in KNOW_ME_QUESTIONS]

        if latest and not await self._has_plan(db, latest.id):
            saved = await self._saved_responses(db, latest.id)
            return PrivateCheckInStartOut(
                checkin_id=latest.id,
                questions=questions,
                total_steps=len(KNOW_ME_QUESTIONS),
                resumed=True,
                step_index=self._step_index_from_saved(saved),
                saved_responses=saved,
            )

        if latest:
            anchor = await self._plan_anchor(db, latest)
            window = _lock_window(anchor)
            if window["locked"]:
                raise FearToFearlessGateError(
                    "locked",
                    (
                        f"Stay with this plan for {window['days_remaining']} more day"
                        f"{'s' if window['days_remaining'] != 1 else ''}. "
                        "Open your last Fear → Fearless plan and do the suggested mocks."
                    ),
                    {
                        "checkin_id": latest.id,
                        "unlocks_at": window["unlocks_at"],
                        "days_remaining": window["days_remaining"],
                        "lock_days": PLAN_LOCK_DAYS,
                    },
                )

        checkin = PrivateStudentCheckIn(
            student_id=user.id,
            organization_id=user.organization_id,
        )
        db.add(checkin)
        await db.flush()

        return PrivateCheckInStartOut(
            checkin_id=checkin.id,
            questions=questions,
            total_steps=len(KNOW_ME_QUESTIONS),
            resumed=False,
            step_index=0,
            saved_responses=[],
        )

    async def save_step_response(
        self,
        db: AsyncSession,
        user: User,
        checkin_id: int,
        step: PrivateCheckInStepIn,
    ) -> dict:
        """Save one question response. Strict ownership check."""
        _require_student(user, "save Fear → Fearless responses")

        checkin = await db.get(PrivateStudentCheckIn, checkin_id)
        if not checkin or checkin.student_id != user.id:
            raise PermissionError("This check-in does not belong to you.")

        resp = PrivateStudentResponse(
            checkin_id=checkin_id,
            question_key=step.question_key,
            response_type=step.response_type,
            response_value={
                "selected_ids": step.selected_ids,
                "free_text": step.free_text,
            },
        )
        db.add(resp)
        await db.flush()
        
        return {
            "response_id": resp.id,
            "question_key": resp.question_key,
            "saved": True,
        }

    async def generate_insight(
        self,
        db: AsyncSession,
        user: User,
        checkin_id: int,
    ) -> PrivateInsightOut:
        """Generate elder-brother insight from completed check-in."""
        _require_student(user, "generate Fear → Fearless insights")

        checkin = await db.get(PrivateStudentCheckIn, checkin_id)
        if not checkin or checkin.student_id != user.id:
            raise PermissionError("This check-in does not belong to you.")

        stmt = select(PrivateStudentResponse).where(
            PrivateStudentResponse.checkin_id == checkin_id
        )
        result = await db.execute(stmt)
        responses = result.scalars().all()

        responses_by_key: dict[str, dict] = {}
        for resp in responses:
            if isinstance(resp.response_value, dict):
                responses_by_key[resp.question_key] = resp.response_value

        existing = (
            await db.execute(
                select(PrivateStudentInsight)
                .where(
                    PrivateStudentInsight.checkin_id == checkin_id,
                    PrivateStudentInsight.student_id == user.id,
                )
                .order_by(PrivateStudentInsight.created_at.desc())
                .limit(1)
            )
        ).scalar_one_or_none()
        if existing:
            if not checkin.completed_at:
                checkin.completed_at = utc_now()
                await db.flush()
            return _insight_row_to_out(existing)

        heuristic = _heuristic_insight(
            responses_by_key, user.first_name or "friend", checkin_id=checkin_id
        )

        payload = heuristic
        source = "heuristic"
        model = None

        if (settings.openai_api_key or "").strip():
            model = settings.know_my_fear_model
            user_prompt = build_insight_user_prompt(responses_by_key)
            try:
                client = AsyncOpenAI(api_key=settings.openai_api_key)
                resp = await client.chat.completions.create(
                    model=model,
                    messages=[
                        {"role": "system", "content": KNOW_ME_INSIGHT_SYSTEM.strip()},
                        {"role": "user", "content": user_prompt},
                    ],
                    temperature=0.8,
                    max_tokens=1600,
                    response_format={"type": "json_object"},
                )
                content = (resp.choices[0].message.content or "").strip()
                payload = _parse_insight_json(
                    content, fallback_heuristic=heuristic, checkin_id=checkin_id
                )
                source = "openai"
            except Exception:
                logger.exception("Know Me insight generation failed; using heuristic")
                payload = heuristic
                source = "heuristic"
                model = None

        payload = payload.model_copy(update={"checkin_id": checkin_id, "source": source, "model": model})
        await _persist_insight(db, user.id, checkin, payload, source, model)
        return payload

    async def get_progress(
        self,
        db: AsyncSession,
        user: User,
    ) -> PrivateProgressOut:
        """Compare first check-in with latest (for 30–45 day follow-up)."""
        _require_student(user, "view Fear → Fearless progress")

        stmt = select(PrivateStudentCheckIn).where(
            PrivateStudentCheckIn.student_id == user.id,
            PrivateStudentCheckIn.completed_at != None,
        ).order_by(PrivateStudentCheckIn.created_at)
        
        result = await db.execute(stmt)
        checkins = result.scalars().all()

        if len(checkins) < 2:
            return PrivateProgressOut(
                days_since_first=0,
                metrics=[],
                growth_summary="This is your first check-in. Come back in 30–45 days to see your growth.",
            )

        first = checkins[0]
        latest = checkins[-1]
        days_diff = (latest.completed_at - first.completed_at).days

        return PrivateProgressOut(
            days_since_first=days_diff,
            metrics=[
                {"metric_key": "confidence", "label": "Placement confidence", "value_before": None, "value_after": None},
                {"metric_key": "clarity", "label": "Clarity on direction", "value_before": None, "value_after": None},
            ],
            growth_summary=f"You've grown over {days_diff} days. Look at how you'd answer these questions now.",
        )

    async def get_active_journey(
        self,
        db: AsyncSession,
        user: User,
        checkin_id: Optional[int] = None,
    ) -> dict[str, Any]:
        """Latest (or requested) plan + 15-day lock + fear factor + history."""
        _require_student(user, "view Fear → Fearless")

        if checkin_id is not None:
            checkin = await db.get(PrivateStudentCheckIn, checkin_id)
            if not checkin or checkin.student_id != user.id:
                raise PermissionError("This check-in does not belong to you.")
        else:
            checkin = await self._latest_checkin(db, user.id)

        history = await self._history_summaries(db, user.id)

        empty = {
            "phase": "empty",
            "can_start": True,
            "locked": False,
            "unlocks_at": None,
            "days_remaining": 0,
            "days_elapsed": 0,
            "lock_days": PLAN_LOCK_DAYS,
            "checkin_id": None,
            "completed_at": None,
            "fear_factor": None,
            "fear_factor_initial": None,
            "insight": None,
            "intervention": None,
            "questions": [q.model_dump() for q in KNOW_ME_QUESTIONS],
            "step_index": 0,
            "saved_responses": [],
            "history": history,
        }
        if not checkin:
            return empty

        has_plan = await self._has_plan(db, checkin.id)
        if not has_plan:
            saved = await self._saved_responses(db, checkin.id)
            return {
                **empty,
                "phase": "form",
                "can_start": False,
                "checkin_id": checkin.id,
                "step_index": self._step_index_from_saved(saved),
                "saved_responses": saved,
            }

        anchor = await self._plan_anchor(db, checkin)
        window = _lock_window(anchor)
        insight_row = (
            await db.execute(
                select(PrivateStudentInsight)
                .where(
                    PrivateStudentInsight.checkin_id == checkin.id,
                    PrivateStudentInsight.student_id == user.id,
                )
                .order_by(PrivateStudentInsight.created_at.desc())
                .limit(1)
            )
        ).scalar_one_or_none()
        intervention = await _intervention.get_intervention_status(
            db, user.id, checkin.id
        )
        insight_out = (
            _insight_row_to_out(insight_row).model_dump()
            if insight_row
            else _insight_from_intervention(checkin.id, intervention)
        )
        phase = "plan" if window["locked"] else "unlocked"
        return {
            "phase": phase,
            "can_start": window["can_start"],
            "locked": window["locked"],
            "unlocks_at": window["unlocks_at"],
            "days_remaining": window["days_remaining"],
            "days_elapsed": window["days_elapsed"],
            "lock_days": PLAN_LOCK_DAYS,
            "checkin_id": checkin.id,
            "completed_at": (
                _as_naive(checkin.completed_at) or anchor
            ).isoformat()
            if (checkin.completed_at or anchor)
            else None,
            "fear_factor": intervention.get("fear_factor"),
            "fear_factor_initial": intervention.get("fear_factor_initial"),
            "insight": insight_out,
            "intervention": intervention,
            "questions": [q.model_dump() for q in KNOW_ME_QUESTIONS],
            "step_index": 0,
            "saved_responses": [],
            "history": history,
        }

    async def _history_summaries(
        self, db: AsyncSession, student_id: int
    ) -> list[dict[str, Any]]:
        checkins = list(
            (
                await db.execute(
                    select(PrivateStudentCheckIn)
                    .where(PrivateStudentCheckIn.student_id == student_id)
                    .order_by(PrivateStudentCheckIn.created_at.desc())
                    .limit(12)
                )
            ).scalars().all()
        )
        out: list[dict[str, Any]] = []
        for row in checkins:
            if not await self._has_plan(db, row.id):
                continue
            insight = (
                await db.execute(
                    select(PrivateStudentInsight)
                    .where(PrivateStudentInsight.checkin_id == row.id)
                    .order_by(PrivateStudentInsight.created_at.desc())
                    .limit(1)
                )
            ).scalar_one_or_none()
            status = await _intervention.get_intervention_status(db, student_id, row.id)
            anchor = await self._plan_anchor(db, row)
            window = _lock_window(anchor)
            out.append(
                {
                    "checkin_id": row.id,
                    "completed_at": (
                        _as_naive(row.completed_at) or anchor
                    ).isoformat()
                    if (row.completed_at or anchor)
                    else None,
                    "headline": (insight.headline if insight else None)
                    or (status.get("fears") or [{}])[0].get("fear_name")
                    or "Your plan",
                    "fear_factor": status.get("fear_factor"),
                    "fear_factor_initial": status.get("fear_factor_initial"),
                    "status": status.get("status"),
                    "locked": window["locked"],
                    "days_remaining": window["days_remaining"],
                }
            )
        return out


def _insight_row_to_out(row: PrivateStudentInsight) -> PrivateInsightOut:
    full = row.full_insight_json if isinstance(row.full_insight_json, dict) else {}
    blockers = []
    for i, b in enumerate(row.blockers or [], 1):
        if isinstance(b, dict):
            blockers.append(
                BlockerItem(
                    order=b.get("order", i),
                    title=str(b.get("title") or ""),
                    student_quote=str(b.get("student_quote") or ""),
                    mentormuni_action=str(b.get("mentormuni_action") or ""),
                )
            )
    actions = []
    for i, a in enumerate((full.get("action_plan") or row.action_plan or []), 1):
        if isinstance(a, dict):
            actions.append(
                ActionItem(
                    priority=a.get("priority", i),
                    action_type=str(a.get("action_type") or ""),
                    description=str(a.get("description") or ""),
                    tool_code=a.get("tool_code"),
                    duration_minutes=a.get("duration_minutes"),
                )
            )
    return PrivateInsightOut(
        checkin_id=row.checkin_id,
        source=row.source if row.source in ("openai", "heuristic") else "heuristic",
        model=row.model,
        headline=row.headline,
        what_i_hear=list(row.what_i_hear or []),
        narrative=str(full.get("narrative") or ""),
        blockers=blockers,
        action_plan=actions,
        call_to_action=str(full.get("call_to_action") or ""),
        closing_line=str(full.get("closing_line") or ""),
    )


def _insight_from_intervention(checkin_id: int, intervention: dict) -> dict:
    fears = intervention.get("fears") or []
    names = [f.get("fear_name") for f in fears if f.get("fear_name")]
    return {
        "checkin_id": checkin_id,
        "source": "heuristic",
        "model": None,
        "headline": "Your plan is still here. Keep working it down to 0.",
        "what_i_hear": names[:3],
        "narrative": "Open the week below and do the suggested mocks. Each one lowers your fear factor.",
        "blockers": [
            {
                "order": i + 1,
                "title": f.get("fear_name") or f"Fear {i + 1}",
                "student_quote": "",
                "mentormuni_action": "Do the suggested mock for this fear.",
            }
            for i, f in enumerate(fears[:3])
        ],
        "action_plan": [],
        "call_to_action": "Do the next suggested mock on your plan.",
        "closing_line": "Fear shrinks when you finish the work — not when you start a new check-in.",
        "private_note": "Your answers here are private. Not shared with TPO, HOD, or campus.",
    }


async def _persist_insight(
    db: AsyncSession,
    student_id: int,
    checkin: PrivateStudentCheckIn,
    payload: PrivateInsightOut,
    source: str,
    model: Optional[str],
) -> None:
    insight = PrivateStudentInsight(
        student_id=student_id,
        checkin_id=checkin.id,
        source=source,
        model=model,
        headline=payload.headline,
        what_i_hear=payload.what_i_hear,
        blockers=[b.model_dump() for b in payload.blockers],
        action_plan=[a.model_dump() for a in payload.action_plan],
        full_insight_json=payload.model_dump(),
    )
    db.add(insight)
    checkin.completed_at = utc_now()
    await db.flush()


def _heuristic_insight(
    responses: dict[str, dict], name: str = "friend", checkin_id: int = -1
) -> PrivateInsightOut:
    """Fallback warm insight without OpenAI."""
    name = name or "friend"
    
    blockers_list: list[BlockerItem] = []
    
    if responses.get("placement_pressure", {}).get("free_text"):
        blockers_list.append(
            BlockerItem(
                order=1,
                title="Unclear starting point",
                student_quote=responses["placement_pressure"]["free_text"][:100],
                mentormuni_action="Start with Skill Readiness Test to see your actual gaps.",
            )
        )
    
    if responses.get("technical_confidence", {}).get("selected_ids"):
        tech_sel = responses["technical_confidence"]["selected_ids"]
        if any(x in tech_sel for x in ["dont_know", "unprepared", "follow_solutions"]):
            blockers_list.append(
                BlockerItem(
                    order=2,
                    title="Technical foundations need clarity",
                    student_quote="I can solve problems when I see them, but struggle on my own.",
                    mentormuni_action="Pick one core skill (Java, DSA) and spend 2 weeks on depth, not breadth.",
                )
            )
    
    if responses.get("project_confidence", {}).get("selected_ids"):
        proj_sel = responses["project_confidence"]["selected_ids"]
        if any(x in proj_sel for x in ["followed_tutorials", "know_not_depth", "afraid_questions"]):
            blockers_list.append(
                BlockerItem(
                    order=3,
                    title="Project confidence is shaky",
                    student_quote="I know the project but not the technical depth.",
                    mentormuni_action="Do a 5-minute mock interview question on your project; find the gaps.",
                )
            )
    
    if not blockers_list:
        blockers_list.append(
            BlockerItem(
                order=1,
                title="You're overthinking",
                student_quote="There's so much to do.",
                mentormuni_action="Start small: one mock interview this week.",
            )
        )
    
    actions: list[ActionItem] = [
        ActionItem(
            priority=1,
            action_type="Assessment",
            description="Take your Skill Readiness Test to see where you actually stand.",
            tool_code="skill_readiness",
            duration_minutes=30,
        ),
        ActionItem(
            priority=2,
            action_type="Practice",
            description="Record a 60-second 'Tell me about yourself' and listen to it.",
            tool_code=None,
            duration_minutes=10,
        ),
        ActionItem(
            priority=3,
            action_type="Mock",
            description="Do a 5-minute low-pressure technical mock.",
            tool_code="interview_mock",
            duration_minutes=15,
        ),
    ]
    
    return PrivateInsightOut(
        checkin_id=checkin_id,
        source="heuristic",
        model=None,
        headline=f"You're caught between clarity and action. Let's fix that.",
        what_i_hear=[
            "You care deeply about placement — that's your strength.",
            "The uncertainty is what's draining you, not lack of ability.",
            "You need a clear, small next step, not a perfect master plan.",
        ],
        narrative=(
            f"Hey {name}, I hear you. What you shared is real, and it's also really common in 3rd/4th year. "
            "The spiral of comparison + 'what should I study' + 'what if I don't get placed' is exhausting. "
            "Here's the thing: you don't need to fix everything this week. You need *clarity* first. "
            "That's what the Skill Readiness Test does — it shows you exactly where you stand. "
            "Then you pick one gap and get good at it. Everything else follows from there."
        ),
        blockers=blockers_list,
        action_plan=actions,
        call_to_action="Let's start with the first step: your Skill Readiness Test.",
        closing_line="You're going to be okay. Let's get to work.",
    )


def _parse_insight_json(
    content: str,
    fallback_heuristic: PrivateInsightOut,
    checkin_id: int = -1,
) -> PrivateInsightOut:
    """Parse OpenAI JSON response; fall back to heuristic if invalid."""
    try:
        data: dict[str, Any] = json.loads(content)
    except json.JSONDecodeError:
        return fallback_heuristic

    try:
        blockers = [
            BlockerItem(
                order=b.get("order", i),
                title=str(b.get("title") or ""),
                student_quote=str(b.get("student_quote") or ""),
                mentormuni_action=str(b.get("mentormuni_action") or ""),
            )
            for i, b in enumerate(data.get("blockers") or [], 1)
        ]
        
        actions = [
            ActionItem(
                priority=a.get("priority", i),
                action_type=str(a.get("action_type") or ""),
                description=str(a.get("description") or ""),
                tool_code=a.get("tool_code"),
                duration_minutes=a.get("duration_minutes"),
            )
            for i, a in enumerate(data.get("action_plan") or [], 1)
        ]
        
        return PrivateInsightOut(
            checkin_id=checkin_id,
            source="openai",
            model=settings.know_my_fear_model,
            headline=str(data.get("headline") or ""),
            what_i_hear=[str(x) for x in (data.get("what_i_hear") or [])],
            narrative=str(data.get("narrative") or ""),
            blockers=blockers,
            action_plan=actions,
            call_to_action=str(data.get("call_to_action") or ""),
            closing_line=str(data.get("closing_line") or ""),
        )
    except Exception:
        logger.exception("Failed to parse insight JSON; returning heuristic")
        return fallback_heuristic

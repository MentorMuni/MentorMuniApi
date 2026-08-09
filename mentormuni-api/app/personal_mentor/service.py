"""Personal voice mentor: student context + OpenAI Realtime session mint."""

from __future__ import annotations

import hashlib
import json
import logging
from typing import Any, Optional

import httpx
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.user import User
from app.personal_mentor.prompt import render_personal_mentor_voice_prompt
from app.personal_mentor.schemas import MentorContextOut, MentorVoiceSessionResponse
from app.student_roadmap import service as roadmap_service

logger = logging.getLogger(__name__)

OPENAI_CLIENT_SECRETS_URL = "https://api.openai.com/v1/realtime/client_secrets"
OPENAI_REALTIME_CALLS_URL = "https://api.openai.com/v1/realtime/calls"
_MALE_VOICES = frozenset({"echo", "ash", "verse", "cedar"})
_DEFAULT_MALE_VOICE = "ash"


class PersonalMentorService:
    async def get_context(self, db: AsyncSession, user: User) -> MentorContextOut:
        ctx = await self._load_context_dict(db, user)
        return MentorContextOut(
            student_name=ctx.get("student_name") or "Student",
            college=ctx.get("college"),
            department=ctx.get("department"),
            week_status=ctx.get("week_status"),
            overall_score=ctx.get("overall_score"),
            scores_by_tool=ctx.get("scores_by_tool") or {},
            top_strengths=ctx.get("top_strengths") or [],
            top_weaknesses=ctx.get("top_weaknesses") or [],
            plan_status=ctx.get("plan_status"),
            plan_summary=ctx.get("plan_summary"),
            next_drive=ctx.get("next_drive"),
            recent_coding=ctx.get("recent_coding") or [],
            greeting_hint=_greeting_hint(ctx),
        )

    async def create_voice_session(
        self,
        db: AsyncSession,
        user: User,
        *,
        voice: Optional[str] = None,
    ) -> MentorVoiceSessionResponse:
        if not (settings.openai_api_key or "").strip():
            raise HTTPException(
                status_code=503,
                detail="Voice mentor is unavailable (OpenAI not configured).",
            )

        ctx = await self._load_context_dict(db, user)
        instructions = render_personal_mentor_voice_prompt(_format_context_block(ctx))
        model = settings.realtime_model
        requested = (voice or _DEFAULT_MALE_VOICE).strip().lower()
        voice_id = requested if requested in _MALE_VOICES else _DEFAULT_MALE_VOICE

        # Conversational mentor: slightly snappier turn-taking than formal interviews.
        payload: dict[str, Any] = {
            "expires_after": {
                "anchor": "created_at",
                "seconds": settings.realtime_client_secret_ttl_seconds,
            },
            "session": {
                "type": "realtime",
                "model": model,
                "instructions": instructions,
                "audio": {
                    "input": {
                        "noise_reduction": {"type": "far_field"},
                        "transcription": {
                            "model": "gpt-4o-mini-transcribe",
                            "language": "en",
                        },
                        "turn_detection": {
                            "type": "server_vad",
                            "threshold": 0.68,
                            "prefix_padding_ms": 250,
                            "silence_duration_ms": 1100,
                            "create_response": True,
                            "interrupt_response": True,
                        },
                    },
                    "output": {
                        "voice": voice_id,
                        "speed": 0.97,
                    },
                },
            },
        }

        headers = {
            "Authorization": f"Bearer {settings.openai_api_key}",
            "Content-Type": "application/json",
        }
        safety_seed = f"mentor|{getattr(user, 'id', '')}|{ctx.get('student_name') or ''}"
        headers["OpenAI-Safety-Identifier"] = hashlib.sha256(
            safety_seed.encode("utf-8")
        ).hexdigest()[:64]

        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                OPENAI_CLIENT_SECRETS_URL,
                headers=headers,
                json=payload,
            )

        if resp.status_code >= 400:
            detail = _safe_openai_error(resp)
            logger.error(
                "Mentor realtime client_secrets failed status=%s detail=%s",
                resp.status_code,
                detail,
            )
            raise HTTPException(status_code=502, detail=detail)

        data = resp.json()
        client_secret = data.get("value")
        expires_at = data.get("expires_at")
        if not client_secret or expires_at is None:
            raise HTTPException(
                status_code=502,
                detail="OpenAI did not return a valid ephemeral client secret",
            )

        preview = instructions.strip().replace("\n", " ")
        if len(preview) > 280:
            preview = preview[:277] + "..."

        return MentorVoiceSessionResponse(
            client_secret=client_secret,
            expires_at=int(expires_at),
            model=model,
            voice=voice_id,
            student_name=ctx.get("student_name") or "Student",
            instructions_preview=preview,
            realtime_calls_url=OPENAI_REALTIME_CALLS_URL,
            context_used=_context_summary(ctx),
        )

    async def _load_context_dict(self, db: AsyncSession, user: User) -> dict[str, Any]:
        name = (getattr(user, "name", None) or "Student").strip() or "Student"
        college = None
        department = None
        org = getattr(user, "organization", None)
        if org is not None:
            college = getattr(org, "name", None) or getattr(org, "code", None)
        dept = getattr(user, "department", None)
        if dept is not None:
            department = getattr(dept, "name", None)

        week_status = None
        overall_score = None
        scores_by_tool: dict[str, float] = {}
        top_strengths: list[str] = []
        top_weaknesses: list[str] = []
        plan_status = None
        plan_summary = None
        next_drive = None
        recent_coding: list[dict[str, Any]] = []

        try:
            analysis = await roadmap_service.get_analysis(db, user)
            week_status = analysis.week_status
            overall_score = analysis.overall_score
            scores_by_tool = dict(analysis.scores_by_tool or {})
            top_strengths = list(analysis.top_strengths or [])[:8]
            top_weaknesses = list(analysis.top_weaknesses or [])[:8]
        except Exception:
            logger.debug("mentor: analysis unavailable", exc_info=True)

        try:
            plan = await roadmap_service.get_latest_plan(db, user)
            plan_status = plan.status
            plan_summary = plan.summary
            if not plan_summary and isinstance(plan.plan, dict):
                plan_summary = plan.plan.get("baseline_summary") or plan.plan.get("title")
        except Exception:
            plan_status = None
            plan_summary = None

        try:
            next_drive = await _load_next_drive(db, user)
        except Exception:
            logger.debug("mentor: drives unavailable", exc_info=True)

        try:
            recent_coding = await _load_recent_coding(db, user)
        except Exception:
            logger.debug("mentor: coding unavailable", exc_info=True)

        return {
            "student_name": name,
            "college": college,
            "department": department,
            "week_status": week_status,
            "overall_score": overall_score,
            "scores_by_tool": scores_by_tool,
            "top_strengths": top_strengths,
            "top_weaknesses": top_weaknesses,
            "plan_status": plan_status,
            "plan_summary": plan_summary,
            "next_drive": next_drive,
            "recent_coding": recent_coding,
        }


async def _load_next_drive(db: AsyncSession, user: User) -> Optional[dict[str, Any]]:
    from datetime import date

    from app.models.upcoming_drive import UpcomingDrive

    org_id = getattr(user, "organization_id", None)
    if not org_id:
        return None
    today = date.today()
    q = (
        select(UpcomingDrive)
        .where(
            UpcomingDrive.organization_id == org_id,
            UpcomingDrive.drive_date >= today,
            UpcomingDrive.deleted_at.is_(None),
        )
        .order_by(UpcomingDrive.drive_date.asc())
        .limit(1)
    )
    row = (await db.execute(q)).scalar_one_or_none()
    if row is None:
        return None
    days = (row.drive_date - today).days if row.drive_date else None
    return {
        "company_name": row.company_name,
        "drive_date": row.drive_date.isoformat() if row.drive_date else None,
        "days_until": days,
    }


async def _load_recent_coding(db: AsyncSession, user: User) -> list[dict[str, Any]]:
    from app.coding.models import CodingSubmission

    q = (
        select(CodingSubmission)
        .where(CodingSubmission.student_id == user.id)
        .order_by(CodingSubmission.created_at.desc())
        .limit(5)
    )
    rows = (await db.execute(q)).scalars().all()
    out: list[dict[str, Any]] = []
    for r in rows:
        out.append(
            {
                "score": getattr(r, "score", None),
                "status": getattr(r, "execution_status", None),
                "language": getattr(r, "language_code", None),
                "created_at": r.created_at.isoformat() if getattr(r, "created_at", None) else None,
            }
        )
    return out


def _format_context_block(ctx: dict[str, Any]) -> str:
    lines = [
        f"Student name: {ctx.get('student_name') or 'Student'}",
        f"College: {ctx.get('college') or '—'}",
        f"Department: {ctx.get('department') or '—'}",
        f"Baseline week status: {ctx.get('week_status') or 'unknown'}",
        f"Overall baseline score: {ctx.get('overall_score') if ctx.get('overall_score') is not None else 'not enough scores yet'}",
        f"Scores by tool: {json.dumps(ctx.get('scores_by_tool') or {}, ensure_ascii=True)}",
        f"Top strengths: {', '.join(ctx.get('top_strengths') or []) or 'none recorded yet'}",
        f"Top weaknesses: {', '.join(ctx.get('top_weaknesses') or []) or 'none recorded yet'}",
        f"90-day plan status: {ctx.get('plan_status') or 'not generated'}",
        f"Plan summary: {ctx.get('plan_summary') or '—'}",
    ]
    drive = ctx.get("next_drive")
    if drive:
        lines.append(
            "Next campus drive: "
            f"{drive.get('company_name')} on {drive.get('drive_date')} "
            f"({drive.get('days_until')} days)"
        )
    else:
        lines.append("Next campus drive: none listed")

    coding = ctx.get("recent_coding") or []
    if coding:
        lines.append(f"Recent coding submissions: {json.dumps(coding, ensure_ascii=True)}")
    else:
        lines.append("Recent coding submissions: none yet")
    return "\n".join(lines)


def _context_summary(ctx: dict[str, Any]) -> dict[str, Any]:
    return {
        "week_status": ctx.get("week_status"),
        "overall_score": ctx.get("overall_score"),
        "plan_status": ctx.get("plan_status"),
        "weakness_count": len(ctx.get("top_weaknesses") or []),
        "has_drive": bool(ctx.get("next_drive")),
        "coding_count": len(ctx.get("recent_coding") or []),
    }


def _greeting_hint(ctx: dict[str, Any]) -> str:
    weaknesses = ctx.get("top_weaknesses") or []
    if weaknesses:
        return f"Want help closing: {weaknesses[0]}?"
    if ctx.get("week_status") != "done":
        return "Ask me how to tackle your current baseline step."
    if ctx.get("plan_status") != "ready":
        return "Baseline done — ask me what to focus on before generating your plan."
    return "Ask about today's prep, a concept, or a project idea."


def _safe_openai_error(resp: httpx.Response) -> str:
    try:
        data = resp.json()
        err = data.get("error") if isinstance(data, dict) else None
        if isinstance(err, dict) and err.get("message"):
            return str(err["message"])[:400]
        if isinstance(data, dict) and data.get("message"):
            return str(data["message"])[:400]
    except Exception:
        pass
    text = (resp.text or "").strip()
    return (text[:400] if text else f"OpenAI error ({resp.status_code})")

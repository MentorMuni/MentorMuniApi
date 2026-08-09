"""Stateless fear reflection — student-private, never written to org tables."""

from __future__ import annotations

import json
import logging
import re
from typing import Any

from fastapi import HTTPException
from openai import AsyncOpenAI

from app.core.config import settings
from app.know_my_fear.catalog import catalog_out, resolve_fears
from app.know_my_fear.prompt import KNOW_MY_FEAR_SYSTEM, build_user_prompt
from app.know_my_fear.schemas import (
    FearCatalogOut,
    FearVsFact,
    KnowMyFearReflection,
    KnowMyFearRequest,
    KnowMyFearResponse,
)
from app.models.user import User

logger = logging.getLogger(__name__)


class KnowMyFearService:
    def get_catalog(self) -> FearCatalogOut:
        return catalog_out()

    async def reflect(self, user: User, body: KnowMyFearRequest) -> KnowMyFearResponse:
        fears = resolve_fears(body.fear_ids)
        if not fears:
            raise HTTPException(status_code=400, detail="Pick at least one valid fear.")

        first_name = _first_name(user)
        heuristic = _heuristic_reflection(fears, body.free_text, first_name)

        if not (settings.openai_api_key or "").strip():
            return KnowMyFearResponse(
                ok=True,
                source="heuristic",
                model=None,
                reflection=heuristic,
            )

        model = settings.know_my_fear_model
        user_prompt = build_user_prompt(
            fears=fears,
            free_text=body.free_text,
            first_name=first_name,
        )
        try:
            client = AsyncOpenAI(api_key=settings.openai_api_key)
            resp = await client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": KNOW_MY_FEAR_SYSTEM.strip()},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0.7,
                max_tokens=1400,
                response_format={"type": "json_object"},
            )
            content = (resp.choices[0].message.content or "").strip()
            reflection = _parse_reflection(content, fallback=heuristic)
            return KnowMyFearResponse(
                ok=True,
                source="openai",
                model=model,
                reflection=reflection,
            )
        except Exception:
            logger.exception("know_my_fear OpenAI failed; using heuristic")
            return KnowMyFearResponse(
                ok=True,
                source="heuristic",
                model=None,
                reflection=heuristic,
            )


def _first_name(user: User) -> str | None:
    raw = getattr(user, "first_name", None) or getattr(user, "username", None)
    if not raw:
        return None
    text = str(raw).strip()
    part = re.split(r"[\s._-]+", text)[0]
    return part[:40] if part else None


def _heuristic_reflection(
    fears: list[dict],
    free_text: str,
    first_name: str | None,
) -> KnowMyFearReflection:
    name = first_name or "friend"
    labels = [f["label"] for f in fears]
    top = labels[0] if labels else "placement fear"
    extra = (free_text or "").strip()

    letter_bits = [
        f"Hey {name} — thanks for saying this out loud here. "
        f"What you picked (“{top}”"
        + (f" and {len(labels) - 1} more" if len(labels) > 1 else "")
        + ") is extremely common in 3rd/4th year. "
        "It does not mean you are finished. It means your brain is loud because placement feels high-stakes.",
        "I got through the same spiral: comparison, English nerves, half-finished projects, "
        "and the ‘what will they say at home’ loop. The way out was never magic confidence — "
        "it was tiny daily reps plus one honest ask for help.",
    ]
    if extra:
        letter_bits.append(
            "What you wrote on the side matters too. Keep that honesty with yourself — "
            "we will turn it into a short plan, not more guilt."
        )
    letter_bits.append(
        "You do not need to fix your whole career tonight. You need one clear week. "
        "Fear shrinks when your calendar has a next action."
    )

    pairs: list[FearVsFact] = []
    for f in fears[:4]:
        pairs.append(
            FearVsFact(
                fear=f["label"],
                fact=_fact_for(f["id"]),
            )
        )
    if not pairs:
        pairs = [
            FearVsFact(
                fear="I'm behind everyone",
                fact="You only see others' highlight reel. Your job is your next 7 days of practice.",
            )
        ]

    week = _week_actions(fears)
    return KnowMyFearReflection(
        headline=f"You're not broken — you're carrying {top.lower()}.",
        letter="\n\n".join(letter_bits),
        you_are_not_alone=[
            "Almost every placed senior had a week they felt already rejected.",
            "FOMO is loudest when you have no plan — silence it with a short checklist.",
            "Asking ‘what should I study?’ is a strength, not a confession of failure.",
        ],
        fear_vs_fact=pairs,
        this_week=week,
        ask_without_shame=(
            "Message one senior or friend today: “I’m preparing for placements — "
            "what did you actually study in the last 30 days?” One ask. No apology essay."
        ),
        closing=(
            "Breathe. You are allowed to start from where you are. "
            "Close this tab a little lighter — then open one practice session."
        ),
    )


def _fact_for(fear_id: str) -> str:
    return {
        "placement_fomo": "Comparison burns energy. A written weekly plan beats scrolling drives.",
        "communication": "Speaking is a skill with reps — 5 minutes aloud daily beats silent worry.",
        "english": "Clear simple English beats fancy vocabulary. Practice short answers, not novels.",
        "technical": "Weak right now ≠ weak forever. Pick one topic and get 70% solid this week.",
        "no_own_project": "Build a tiny real thing in 7–10 days. Ownership beats a cloned mega-repo.",
        "what_to_study": "Order: aptitude basics → 1 core skill → resume story → mock interviews.",
        "where_from": "One trusted path > ten tabs. Stick to one course/notes set for 14 days.",
        "which_skills": "For most service/product campus roles: aptitude + one stack + projects + mocks.",
        "aptitude": "Aptitude is trainable. 25 focused minutes daily compounds fast.",
        "hr_fomo": "HR is a script you can rehearse: story, projects, gaps, why this company.",
        "interview_fear": "Nerves are normal. Mock interviews convert fear into muscle memory.",
        "ask_for_help": "Seniors remember being lost. A short, specific ask is respected.",
        "family_pressure": "You can care about home and still prepare one day at a time.",
        "friends_placed": "Their offer is not your scorecard. Parallel paths are normal.",
        "plan_b": "Off-campus, internships, and smaller firms are valid paths — not shame.",
    }.get(
        fear_id,
        "Fear is a signal to prepare, not a verdict on your worth.",
    )


def _week_actions(fears: list[dict]) -> list[str]:
    ids = {f["id"] for f in fears}
    actions: list[str] = []
    if ids & {"aptitude", "placement_fomo", "what_to_study"}:
        actions.append("25–30 min aptitude daily (percentages, ratios, puzzles) — same time each day.")
    if ids & {"technical", "which_skills", "where_from"}:
        actions.append("Pick one skill track for 14 days; finish one concept + 5 practice questions/day.")
    if ids & {"no_own_project"}:
        actions.append("Start a tiny project: problem → 3 features → GitHub README by day 10.")
    if ids & {"communication", "english", "interview_fear", "hr_fomo"}:
        actions.append("Record a 60-second ‘Tell me about yourself’ daily; listen once and fix one line.")
    if ids & {"ask_for_help", "friends_placed", "family_pressure", "plan_b"}:
        actions.append("Ask one senior for their real prep routine; write your Plan A + calm Plan B.")
    if not actions:
        actions.append("Open Practice or Coding Round and finish one honest session today.")
    actions.append("Protect sleep and one short walk — tired brains invent worse stories.")
    return actions[:5]


def _parse_reflection(content: str, *, fallback: KnowMyFearReflection) -> KnowMyFearReflection:
    try:
        data: dict[str, Any] = json.loads(content)
    except json.JSONDecodeError:
        return fallback

    def strs(key: str, nmin: int = 0, nmax: int = 6) -> list[str]:
        raw = data.get(key) or []
        if not isinstance(raw, list):
            return getattr(fallback, key) if hasattr(fallback, key) else []
        out = [str(x).strip() for x in raw if str(x).strip()]
        if len(out) < nmin:
            return getattr(fallback, key)
        return out[:nmax]

    pairs_raw = data.get("fear_vs_fact") or []
    pairs: list[FearVsFact] = []
    if isinstance(pairs_raw, list):
        for item in pairs_raw[:4]:
            if not isinstance(item, dict):
                continue
            fear = str(item.get("fear") or "").strip()
            fact = str(item.get("fact") or "").strip()
            if fear and fact:
                pairs.append(FearVsFact(fear=fear, fact=fact))
    if len(pairs) < 2:
        pairs = fallback.fear_vs_fact

    headline = str(data.get("headline") or "").strip() or fallback.headline
    letter = str(data.get("letter") or "").strip() or fallback.letter
    alone = strs("you_are_not_alone", 2, 4) or fallback.you_are_not_alone
    week = strs("this_week", 3, 5) or fallback.this_week
    ask = str(data.get("ask_without_shame") or "").strip() or fallback.ask_without_shame
    closing = str(data.get("closing") or "").strip() or fallback.closing

    return KnowMyFearReflection(
        headline=headline,
        letter=letter,
        you_are_not_alone=alone,
        fear_vs_fact=pairs,
        this_week=week,
        ask_without_shame=ask,
        closing=closing,
    )

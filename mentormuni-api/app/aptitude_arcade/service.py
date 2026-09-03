"""Generate Aptitude Arcade question packs via OpenAI."""

from __future__ import annotations

import json
import logging
import math
import re
from typing import Any

from openai import AsyncOpenAI

from app.aptitude_arcade.prompt import ARCADE_SYSTEM, build_arcade_user_prompt
from app.aptitude_arcade.schemas import GAME_IDS, ArcadeGenerateOut
from app.core.config import settings

logger = logging.getLogger(__name__)

DEFAULT_COUNT = 30


class ArcadeError(Exception):
    def __init__(self, status_code: int, message: str):
        super().__init__(message)
        self.status_code = status_code
        self.message = message


def _strip_fences(raw: str) -> str:
    text = (raw or "").strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    return text.strip()


def _parse_json(content: str) -> dict[str, Any]:
    text = _strip_fences(content)
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        start = text.find("{")
        end = text.rfind("}")
        if start >= 0 and end > start:
            data = json.loads(text[start : end + 1])
        else:
            raise ArcadeError(502, "Model returned invalid JSON.") from None
    if not isinstance(data, dict):
        raise ArcadeError(502, "Model returned invalid JSON object.")
    return data


def _letters_only(seq: list[Any]) -> list[str]:
    out: list[str] = []
    for item in seq:
        s = str(item).strip().upper()
        if not s:
            continue
        out.append(s[0] if len(s) > 1 and s[0].isalpha() else s)
    return out


def _normalize_seating(items: list[Any], count: int) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for raw in items:
        if not isinstance(raw, dict):
            continue
        solution = _letters_only(list(raw.get("solution") or []))
        seats = int(raw.get("seats") or len(solution) or 4)
        seats = max(3, min(6, seats))
        if len(solution) != seats or len(set(solution)) != seats:
            continue
        clues = [str(c).strip() for c in (raw.get("clues") or []) if str(c).strip()]
        if len(clues) < 2:
            continue
        out.append(
            {
                "clues": clues[:8],
                "seats": seats,
                "solution": solution,
                "facing": str(raw.get("facing") or "Linear row, left → right."),
                "solutionText": str(raw.get("solutionText") or " – ".join(solution)),
            }
        )
        if len(out) >= count:
            break
    return out


def _normalize_blood(items: list[Any], count: int) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for raw in items:
        if not isinstance(raw, dict):
            continue
        q = str(raw.get("q") or "").strip()
        options = [str(o).strip() for o in (raw.get("options") or []) if str(o).strip()]
        answer = str(raw.get("answer") or "").strip()
        if not q or len(options) < 4 or answer not in options:
            # try case-insensitive match
            matched = next((o for o in options if o.lower() == answer.lower()), None)
            if not matched:
                continue
            answer = matched
        out.append(
            {
                "q": q,
                "options": options[:4],
                "answer": answer,
                "solution": str(raw.get("solution") or raw.get("tip") or "Trace the relation chain."),
                "tip": str(raw.get("tip") or raw.get("solution") or "Map generations carefully."),
            }
        )
        if len(out) >= count:
            break
    return out


def _normalize_train(items: list[Any], count: int) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for raw in items:
        if not isinstance(raw, dict):
            continue
        try:
            length = float(raw.get("length"))
            speed_a = float(raw.get("speedA"))
            speed_b = float(raw.get("speedB"))
        except (TypeError, ValueError):
            continue
        if length <= 0 or speed_a <= 0 or speed_b <= 0:
            continue
        opposite = bool(raw.get("opposite", True))
        if opposite:
            rel = speed_a + speed_b
        else:
            if speed_a <= speed_b:
                speed_a, speed_b = max(speed_a, speed_b + 10), min(speed_a, speed_b)
            rel = speed_a - speed_b
        if rel <= 0:
            continue
        answer = length / rel
        out.append(
            {
                "label": str(
                    raw.get("label")
                    or ("Opposite direction — meet" if opposite else "Same direction — chase")
                ),
                "length": length,
                "speedA": speed_a,
                "speedB": speed_b,
                "opposite": opposite,
                "question": str(
                    raw.get("question")
                    or f"Distance {length} km. Speeds {speed_a} & {speed_b} km/h. Time (hours)?"
                ),
                "answer": answer,
                "formula": str(raw.get("formula") or f"{length} / {rel}"),
                "solution": str(
                    raw.get("solution")
                    or f"Relative speed = {rel} km/h → time = {answer:.4g} hours."
                ),
            }
        )
        if len(out) >= count:
            break
    return out


def _normalize_work(items: list[Any], count: int) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for i, raw in enumerate(items):
        if not isinstance(raw, dict):
            continue
        try:
            workers = int(raw.get("workers"))
            days = int(raw.get("days"))
            target = int(raw.get("targetDays"))
        except (TypeError, ValueError):
            continue
        if workers < 2 or days < 2 or target < 1 or target >= days:
            continue
        total = workers * days
        needed = math.ceil(total / target)
        out.append(
            {
                "title": str(raw.get("title") or f"Job pack {i + 1}"),
                "workers": workers,
                "days": days,
                "targetDays": target,
                "tip": str(raw.get("tip") or "Man-days = workers × days."),
                "solution": str(
                    raw.get("solution")
                    or f"{workers} × {days} = {total} man-days. For {target} days → {needed} workers."
                ),
            }
        )
        if len(out) >= count:
            break
    return out


def _normalize_series(items: list[Any], count: int) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for raw in items:
        if not isinstance(raw, dict):
            continue
        nums_raw = list(raw.get("nums") or [])
        if len(nums_raw) < 4:
            continue
        nums: list[Any] = []
        for n in nums_raw[:5]:
            if str(n).strip() == "?":
                nums.append("?")
            else:
                try:
                    nums.append(int(n))
                except (TypeError, ValueError):
                    try:
                        nums.append(float(n))
                    except (TypeError, ValueError):
                        nums = []
                        break
        if not nums or nums[-1] != "?":
            # force trailing ?
            if len(nums) >= 4 and "?" not in nums:
                nums = nums[:4] + ["?"]
            else:
                continue
        try:
            answer = raw.get("answer")
            answer = int(answer) if float(answer) == int(float(answer)) else float(answer)
        except (TypeError, ValueError):
            continue
        out.append(
            {
                "nums": nums,
                "answer": answer,
                "rule": str(raw.get("rule") or "Find the pattern."),
                "solution": str(raw.get("solution") or f"Missing term = {answer}."),
            }
        )
        if len(out) >= count:
            break
    return out


_NORMALIZERS = {
    "seating_shuffle": _normalize_seating,
    "family_tree_rush": _normalize_blood,
    "rail_rush": _normalize_train,
    "factory_floor": _normalize_work,
    "pattern_pulse": _normalize_series,
}


class AptitudeArcadeService:
    async def generate(self, *, game_id: str, count: int = DEFAULT_COUNT) -> ArcadeGenerateOut:
        if game_id not in GAME_IDS:
            raise ArcadeError(400, "Unknown arcade game.")
        count = max(10, min(30, int(count or DEFAULT_COUNT)))
        api_key = (settings.openai_api_key or "").strip()
        if not api_key:
            raise ArcadeError(503, "OpenAI is not configured on the server.")

        model = (getattr(settings, "aptitude_arcade_model", None) or "gpt-4.1-mini").strip()
        user_prompt = build_arcade_user_prompt(game_id=game_id, count=count)

        try:
            client = AsyncOpenAI(api_key=api_key)
            resp = await client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": ARCADE_SYSTEM},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0.75,
                max_tokens=12000,
                response_format={"type": "json_object"},
            )
            content = (resp.choices[0].message.content or "").strip()
        except Exception as exc:
            logger.exception("Aptitude Arcade OpenAI call failed")
            raise ArcadeError(502, "Could not generate questions. Please try again.") from exc

        data = _parse_json(content)
        raw_questions = data.get("questions")
        if not isinstance(raw_questions, list):
            raise ArcadeError(502, "Model response missing questions array.")

        normalizer = _NORMALIZERS[game_id]
        questions = normalizer(raw_questions, count)
        if len(questions) < max(8, count // 2):
            raise ArcadeError(
                502,
                f"Only {len(questions)} valid questions generated. Please try again.",
            )

        # If slightly short, keep what we have (still replaces the old pack).
        return ArcadeGenerateOut(
            game_id=game_id,  # type: ignore[arg-type]
            count=len(questions),
            questions=questions,
            source="openai",
            model=model,
        )

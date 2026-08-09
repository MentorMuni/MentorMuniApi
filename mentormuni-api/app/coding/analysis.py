"""OpenAI coding analysis — coaching only; never sets official score."""

from __future__ import annotations

import json
import logging
from typing import Any, Optional

from openai import AsyncOpenAI
from pydantic import BaseModel, Field

from app.core.config import settings
from app.services.coding_analysis_prompt import (
    CODING_ANALYSIS_SYSTEM,
    PROMPT_VERSION,
    render_coding_analysis_prompt,
)
from app.services.guard_layer import GuardLayer

logger = logging.getLogger("coding.analysis")

ANALYSIS_MODEL = "gpt-4.1"


class ConstraintAwarenessModel(BaseModel):
    understood_constraints: bool = False
    complexity_appropriate_for_constraints: bool = False
    missed_scalable_approach: bool = False
    notes: str = ""


class CodingAnalysisPayload(BaseModel):
    overall_coaching_score: float = Field(ge=0, le=100)
    correctness: dict[str, Any] = Field(default_factory=dict)
    approach: dict[str, Any] = Field(default_factory=dict)
    complexity: dict[str, Any] = Field(default_factory=dict)
    code_quality: dict[str, Any] = Field(default_factory=dict)
    edge_cases: dict[str, Any] = Field(default_factory=dict)
    constraint_awareness: ConstraintAwarenessModel = Field(default_factory=ConstraintAwarenessModel)
    mistakes: list[dict[str, Any]] = Field(default_factory=list)
    better_approach: dict[str, Any] = Field(default_factory=dict)
    beginner_explanation: str = ""
    strengths: list[str] = Field(default_factory=list)
    learning_gaps: list[str] = Field(default_factory=list)
    next_learning_focus: list[str] = Field(default_factory=list)


class CodingAnalysisService:
    def __init__(self) -> None:
        self._client = AsyncOpenAI(api_key=settings.openai_api_key)
        self._guard = GuardLayer(timeout=settings.llm_timeout_seconds, max_retries=1)

    @property
    def prompt_version(self) -> str:
        return PROMPT_VERSION

    async def analyze(self, **kwargs: Any) -> CodingAnalysisPayload:
        prompt = render_coding_analysis_prompt(**kwargs)

        async def _call() -> str:
            resp = await self._client.chat.completions.create(
                model=ANALYSIS_MODEL,
                temperature=0.2,
                response_format={"type": "json_object"},
                messages=[
                    {"role": "system", "content": CODING_ANALYSIS_SYSTEM},
                    {"role": "user", "content": prompt},
                ],
            )
            return resp.choices[0].message.content or "{}"

        raw = await self._guard.run_with_timeout(_call())
        data = json.loads(raw)
        return CodingAnalysisPayload.model_validate(data)

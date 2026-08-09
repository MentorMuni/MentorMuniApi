"""OpenAI generation client for coding bank problems.

Does not call production student APIs. Rejects non-JSON / schema-invalid output.
"""

from __future__ import annotations

import json
import logging
from typing import Any, Optional

from app.coding_bank import PROMPT_VERSION
from app.coding_bank.curriculum import GenerationSpec
from app.coding_bank.prompt import (
    CODING_PROBLEM_GENERATION_SYSTEM,
    openai_response_format,
    render_generation_user_prompt,
)
from app.coding_bank.schemas import GeneratedProblemContract
from app.coding_bank.validators.content import SchemaValidator

logger = logging.getLogger(__name__)


class GenerationError(Exception):
    pass


class CodingProblemGenerator:
    def __init__(
        self,
        *,
        openai_client: Any | None = None,
        model: str = "gpt-4.1-mini",
        prompt_version: str = PROMPT_VERSION,
    ) -> None:
        self.client = openai_client
        self.model = model
        self.prompt_version = prompt_version
        self.schema_validator = SchemaValidator()

    def build_messages(
        self,
        spec: GenerationSpec,
        *,
        avoid_titles: list[str] | None = None,
        avoid_slugs: list[str] | None = None,
        company_name: str | None = None,
    ) -> list[dict[str, str]]:
        return [
            {"role": "system", "content": CODING_PROBLEM_GENERATION_SYSTEM},
            {
                "role": "user",
                "content": render_generation_user_prompt(
                    difficulty=spec.difficulty,
                    topic=spec.topic,
                    pattern=spec.pattern,
                    expected_time_complexity=spec.expected_time_complexity,
                    expected_space_complexity=spec.expected_space_complexity,
                    avoid_titles=avoid_titles,
                    avoid_slugs=avoid_slugs,
                    extra_notes=spec.notes or None,
                    company_name=company_name,
                ),
            },
        ]

    def parse_model_json(self, raw: str | dict[str, Any]) -> GeneratedProblemContract:
        if isinstance(raw, dict):
            payload = raw
        else:
            text = raw.strip()
            if text.startswith("```"):
                # Reject fenced output — require bare JSON for strictness
                raise GenerationError("model returned markdown fences; expected bare JSON")
            try:
                payload = json.loads(text)
            except json.JSONDecodeError as e:
                raise GenerationError(f"malformed JSON: {e}") from e
        contract, report = self.schema_validator.validate(payload)
        if contract is None:
            raise GenerationError(f"schema validation failed: {report.errors}")
        return contract

    async def generate_one(
        self,
        spec: GenerationSpec,
        *,
        avoid_titles: list[str] | None = None,
        avoid_slugs: list[str] | None = None,
        company_name: str | None = None,
    ) -> GeneratedProblemContract:
        if self.client is None:
            raise GenerationError(
                "openai_client not configured — set OPENAI_API_KEY to enable generation"
            )
        messages = self.build_messages(
            spec,
            avoid_titles=avoid_titles,
            avoid_slugs=avoid_slugs,
            company_name=company_name,
        )
        # Prefer structured outputs when the client supports it.
        kwargs: dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "temperature": 0.4,
        }
        try:
            kwargs["response_format"] = openai_response_format()
            resp = await self._chat(kwargs)
        except Exception:
            # Fallback without response_format if SDK/model rejects schema wrapper
            kwargs.pop("response_format", None)
            resp = await self._chat(kwargs)
        content = self._extract_content(resp)
        return self.parse_model_json(content)

    async def _chat(self, kwargs: dict[str, Any]) -> Any:
        client = self.client
        # Support both AsyncOpenAI and sync OpenAI
        create = getattr(getattr(client, "chat", None), "completions", None)
        if create is None:
            raise GenerationError("openai client missing chat.completions")
        fn = create.create
        result = fn(**kwargs)
        if hasattr(result, "__await__"):
            return await result
        return result

    @staticmethod
    def _extract_content(resp: Any) -> str:
        try:
            return resp.choices[0].message.content or ""
        except Exception as e:
            raise GenerationError(f"unexpected OpenAI response shape: {e}") from e

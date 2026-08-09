"""Strict structured contract for AI-generated coding problems.

Malformed LLM output is rejected — never trust free-form text.
"""

from __future__ import annotations

import re
from typing import Any, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

Difficulty = Literal["easy", "medium", "hard"]
LanguageCode = Literal["python", "cpp", "java"]
TestCategory = Literal[
    "normal",
    "boundary",
    "minimum",
    "maximum",
    "duplicates",
    "empty",
    "single",
    "negative",
    "adversarial",
    "large",
]


class GeneratedExample(BaseModel):
    model_config = ConfigDict(extra="forbid")

    input: str = Field(min_length=0)
    output: str = Field(min_length=0)
    explanation: Optional[str] = None


class GeneratedStarterCode(BaseModel):
    model_config = ConfigDict(extra="forbid")

    language: LanguageCode
    code: str = Field(min_length=1)


class GeneratedReferenceSolution(BaseModel):
    model_config = ConfigDict(extra="forbid")

    language: LanguageCode
    code: str = Field(min_length=1)
    notes: Optional[str] = None


class GeneratedTestCase(BaseModel):
    model_config = ConfigDict(extra="forbid")

    input: str
    # LLM may propose expected_output; validators overwrite from reference execution.
    expected_output: Optional[str] = None
    is_hidden: bool = False
    weight: float = Field(default=1.0, gt=0)
    category: TestCategory = "normal"
    order_index: Optional[int] = None


class GeneratedProblemContract(BaseModel):
    """Canonical generation JSON schema (schema-validated before persistence)."""

    model_config = ConfigDict(extra="forbid")

    title: str = Field(min_length=3, max_length=255)
    slug: str = Field(min_length=3, max_length=160)
    difficulty: Difficulty
    topics: list[str] = Field(min_length=1, max_length=8)
    patterns: list[str] = Field(min_length=1, max_length=8)
    problem_statement: str = Field(min_length=40)
    input_format: str = Field(min_length=5)
    output_format: str = Field(min_length=5)
    constraints: str = Field(min_length=5)
    examples: list[GeneratedExample] = Field(min_length=1, max_length=5)
    explanation: str = Field(min_length=20)
    expected_time_complexity: str = Field(min_length=2, max_length=64)
    expected_space_complexity: str = Field(min_length=2, max_length=64)
    supported_languages: list[LanguageCode] = Field(min_length=1)
    starter_code: list[GeneratedStarterCode] = Field(min_length=1)
    reference_solutions: list[GeneratedReferenceSolution] = Field(min_length=1)
    candidate_test_cases: list[GeneratedTestCase] = Field(min_length=5, max_length=40)

    @field_validator("slug")
    @classmethod
    def _slug_format(cls, v: str) -> str:
        s = v.strip().lower()
        if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", s):
            raise ValueError("slug must be kebab-case [a-z0-9-]")
        return s

    @field_validator("topics", "patterns")
    @classmethod
    def _normalize_tags(cls, v: list[str]) -> list[str]:
        out = [t.strip().lower() for t in v if t and t.strip()]
        if not out:
            raise ValueError("at least one non-empty tag required")
        return out

    @field_validator("expected_time_complexity", "expected_space_complexity")
    @classmethod
    def _complexity_shape(cls, v: str) -> str:
        s = v.strip()
        if not re.search(r"O\s*\(", s, re.IGNORECASE):
            raise ValueError("complexity must include Big-O notation like O(...)")
        return s

    @model_validator(mode="after")
    def _consistency(self) -> GeneratedProblemContract:
        langs = set(self.supported_languages)
        starter_langs = {s.language for s in self.starter_code}
        ref_langs = {r.language for r in self.reference_solutions}
        if not starter_langs.issubset(langs):
            raise ValueError("starter_code languages must be in supported_languages")
        if not ref_langs.issubset(langs):
            raise ValueError("reference_solutions languages must be in supported_languages")
        if "python" not in ref_langs:
            # Pipeline prefers a trusted Python reference for deterministic validation hooks.
            raise ValueError("at least one python reference solution is required")
        categories = {t.category for t in self.candidate_test_cases}
        if "normal" not in categories:
            raise ValueError("candidate_test_cases must include at least one 'normal' case")
        if len(categories) < 3:
            raise ValueError("candidate_test_cases must cover at least 3 distinct categories")
        return self

    def primary_topic(self) -> str:
        return self.topics[0]

    def primary_pattern(self) -> str:
        return self.patterns[0]

    def starter_map(self) -> dict[str, str]:
        return {s.language: s.code for s in self.starter_code}

    def to_persistence_dict(self) -> dict[str, Any]:
        return self.model_dump(mode="json")


# JSON Schema exported for OpenAI response_format / docs
GENERATED_PROBLEM_JSON_SCHEMA: dict[str, Any] = GeneratedProblemContract.model_json_schema()

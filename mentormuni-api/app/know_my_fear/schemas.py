"""Request/response for student-private fear reflection."""

from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field, field_validator


class FearCatalogItem(BaseModel):
    id: str
    label: str
    blurb: str
    group: str


class FearCatalogOut(BaseModel):
    privacy_note: str
    groups: list[dict]
    fears: list[FearCatalogItem]


class FearSelectionIn(BaseModel):
    id: str = Field(..., min_length=1, max_length=64)
    intensity: Optional[int] = Field(default=None, ge=1, le=5)


class KnowMyFearRequest(BaseModel):
    fear_ids: list[FearSelectionIn] = Field(..., min_length=1, max_length=12)
    free_text: str = Field(default="", max_length=2000)

    @field_validator("free_text")
    @classmethod
    def strip_text(cls, v: str) -> str:
        return (v or "").strip()


class FearVsFact(BaseModel):
    fear: str
    fact: str


class KnowMyFearReflection(BaseModel):
    headline: str
    letter: str
    you_are_not_alone: list[str]
    fear_vs_fact: list[FearVsFact]
    this_week: list[str]
    ask_without_shame: str
    closing: str


class KnowMyFearResponse(BaseModel):
    ok: bool = True
    source: Literal["openai", "heuristic"]
    model: Optional[str] = None
    privacy: str = (
        "Private to you. Not shared with TPO, HOD, or your college dashboard."
    )
    reflection: KnowMyFearReflection

"""Student-safe browse + practice-resolve schemas."""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class TopicCountOut(BaseModel):
    topic: str
    problem_count: int
    difficulties: list[str] = Field(default_factory=list)
    patterns: list[str] = Field(default_factory=list)


class TopicCatalogOut(BaseModel):
    items: list[TopicCountOut]
    audience: str = "engineering_campus_placement_year4"


class BankProblemOut(BaseModel):
    """Published problem card — never includes tests, refs, or evidence_json."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    slug: str
    title: str
    difficulty: str
    topic: Optional[str] = None
    pattern: Optional[str] = None
    summary: Optional[str] = None
    expected_time_complexity: Optional[str] = None
    company_name: Optional[str] = None
    role_name: Optional[str] = None
    relevance_label: Optional[str] = None
    why_this_matters: Optional[str] = None
    assessment_slug: Optional[str] = None


class BankProblemListOut(BaseModel):
    items: list[BankProblemOut]
    topic: Optional[str] = None
    difficulty: Optional[str] = None
    total: int = 0


class PracticeResolveRequest(BaseModel):
    """Free-text topic + difficulty → practice assessment (bank first, generate if needed)."""

    topic: str = Field(..., min_length=2, max_length=120)
    difficulty: str = Field(default="easy", max_length=32)
    company_key: Optional[str] = Field(default=None, max_length=160)
    company_name: Optional[str] = Field(default=None, max_length=160)
    allow_generate: bool = True
    max_problems: int = Field(default=1, ge=1, le=3)


class PracticeResolveOut(BaseModel):
    source: str  # bank | generated | mixed
    assessment_id: int
    assessment_slug: str
    title: str
    topic: str
    difficulty: str
    problem_count: int
    generated: bool = False
    message: Optional[str] = None
    problems: list[BankProblemOut] = Field(default_factory=list)

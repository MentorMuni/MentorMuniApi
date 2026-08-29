"""Pydantic schemas for Student Intelligence P0 APIs."""

from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel, Field


class StudentTargetIn(BaseModel):
    target_companies: list[str] = Field(default_factory=list)
    target_tier: str = "mass_recruiter"
    target_readiness: int = 85


class StudentTargetOut(BaseModel):
    target_companies: list[str]
    target_tier: str
    target_readiness: int


class AttemptIn(BaseModel):
    tool_code: str
    topic_nodes: list[str] = Field(default_factory=list)
    modality: Optional[str] = None
    difficulty: Optional[int] = None
    score: Optional[float] = None
    accuracy: Optional[float] = None
    time_taken_s: Optional[int] = None
    technical_score: Optional[float] = None
    communication_score: Optional[float] = None
    mistakes: list[str] = Field(default_factory=list)
    attempt_number: Optional[int] = 1
    widget_spec: Optional[dict[str, Any]] = None
    item_embeddings: Optional[list[float]] = None
    transcript_ref: Optional[str] = None
    completed_at: Optional[str] = None
    within_time: bool = True
    pool: Optional[str] = None  # NEW | RETRY | VERIFY — default inferred


class TaskCompleteIn(BaseModel):
    local_date: Optional[str] = None
    plan_id: Optional[int] = None
    score: Optional[float] = None
    text_hash: Optional[str] = None
    source: Optional[str] = "manual"


class TaskSkipIn(BaseModel):
    local_date: Optional[str] = None
    plan_id: Optional[int] = None
    reason: Optional[str] = "manual"
    text_hash: Optional[str] = None

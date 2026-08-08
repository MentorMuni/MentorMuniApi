"""Pydantic schemas for Company Intelligence API."""

from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel, Field


class EnsureCompanyIntelRequest(BaseModel):
    company: str = Field(..., min_length=1, max_length=160)
    role: str = Field(default="Software Engineer", min_length=1, max_length=160)
    country: str = Field(default="India", min_length=1, max_length=80)
    force_refresh: bool = False


class CompanyIntelSummaryOut(BaseModel):
    id: int
    slug: str
    company: str
    role: str
    country: str
    status: str
    overall_confidence: Optional[float] = None
    evidence_strength: Optional[str] = None
    last_updated_estimate: Optional[str] = None
    hiring_type: Optional[str] = None
    technical_depth: Optional[str] = None
    rounds_count: Optional[int] = None


class CompanyIntelOut(BaseModel):
    id: int
    slug: str
    company: str
    role: str
    country: str
    status: str
    overall_confidence: Optional[float] = None
    evidence_strength: Optional[str] = None
    last_updated_estimate: Optional[str] = None
    error_message: Optional[str] = None
    prompt_version: Optional[str] = None
    model: Optional[str] = None
    completed_at: Optional[str] = None
    payload: Optional[dict[str, Any]] = None


class CompanyIntelListOut(BaseModel):
    items: list[CompanyIntelSummaryOut]
    catalog: list[dict[str, str]] = []

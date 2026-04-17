from pydantic import BaseModel, ConfigDict, Field
from typing import List, Optional


class AtsScoreEstimate(BaseModel):
    """LLM estimate of shortlist-style ATS band (separate from heuristic 0–100 scores)."""

    model_config = ConfigDict(extra="ignore")

    score: str = Field(default="", description='e.g. "8/10"')
    label: Optional[str] = Field(
        default=None,
        description="e.g. Low | Moderate | High shortlist probability",
    )
    reason: str = Field(default="")


class ScoreBreakdown(BaseModel):
    """LLM sub-scores on /10 scale (narrative; separate from server heuristics)."""

    model_config = ConfigDict(extra="ignore")

    keyword_match: str = Field(default="", description='e.g. "7/10"')
    impact: str = Field(default="")
    structure: str = Field(default="")
    ats_readability: str = Field(default="")


class SectionRewrites(BaseModel):
    """Suggested rewrites for key resume sections (LLM enrichment)."""

    model_config = ConfigDict(extra="ignore")

    headline: Optional[str] = None
    summary: Optional[str] = Field(default=None, description="2–3 line professional summary for resume")
    skills: Optional[str] = None
    project_or_experience: Optional[List[str]] = None


class ResumeAtsResponse(BaseModel):
    """Response shape aligned with frontend normalizeAtsResponse (primary keys)."""

    score: int = Field(..., ge=0, le=100, description="Overall ATS-style score")
    ats: int = Field(..., ge=0, le=100, description="ATS compatibility / parseability")
    keywords: int = Field(..., ge=0, le=100, description="Keyword alignment with target role")
    formatting: int = Field(..., ge=0, le=100)
    impact: int = Field(..., ge=0, le=100)
    summary: str
    matched_keywords: List[str] = Field(default_factory=list)
    missing_keywords: List[str] = Field(default_factory=list)
    fixes: List[str] = Field(
        default_factory=list,
        description="Prioritized changes to improve shortlisting (resume content)",
    )
    strengths: List[str] = Field(
        default_factory=list,
        description="What already helps recruiter search and screening",
    )
    portal_tips: List[str] = Field(
        default_factory=list,
        description="Naukri + LinkedIn specific visibility and profile tips",
    )

    # Optional LLM enrichment (resume ATS prompt v2)
    candidate_type: Optional[str] = Field(
        default=None,
        description="college_student | experienced | fresher (from LLM when enabled)",
    )
    inferred_role: Optional[str] = Field(
        default=None,
        description="Role inferred by LLM from resume (when enabled)",
    )
    top_resume_killers: List[str] = Field(default_factory=list)
    keyword_gaps: List[str] = Field(default_factory=list)
    rewrite_examples: List[str] = Field(default_factory=list)
    section_rewrites: Optional[SectionRewrites] = None
    positioning_improvement: List[str] = Field(default_factory=list)
    score_breakdown: Optional[ScoreBreakdown] = Field(
        default=None,
        description="LLM /10-style breakdown (keyword, impact, structure, ATS readability)",
    )
    ats_score_estimate: Optional[AtsScoreEstimate] = None
    priority_action_plan: List[str] = Field(default_factory=list)

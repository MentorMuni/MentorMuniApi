from pydantic import BaseModel, Field
from typing import List


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

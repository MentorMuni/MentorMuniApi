"""Coding assessment routes (start / problem / draft / run / submit / analysis)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.coding import practice as coding_practice
from app.coding import service as coding_service
from app.coding.browse_schemas import (
    BankProblemListOut,
    PracticeResolveOut,
    PracticeResolveRequest,
    TopicCatalogOut,
)
from app.coding.schemas import (
    AnalysisOut,
    AssessmentListOut,
    AssessmentSummaryOut,
    AttemptOut,
    AttemptProblemOut,
    DraftOut,
    DraftUpsertRequest,
    RunCreateRequest,
    RunOut,
    SubmissionCreateRequest,
    SubmissionListOut,
    SubmissionOut,
)
from app.common.deps import get_db, require_api_key, require_roles
from app.models.enums import RoleCode
from app.models.user import User

router = APIRouter(
    prefix="/api/coding",
    tags=["Coding Assessment"],
    dependencies=[Depends(require_api_key)],
)


@router.get("/assessments", response_model=AssessmentListOut)
async def list_assessments(
    company_key: str | None = Query(default=None, max_length=160),
    topic: str | None = Query(default=None, max_length=80),
    difficulty: str | None = Query(default=None, max_length=32),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_roles(RoleCode.STUDENT.value)),
) -> AssessmentListOut:
    """List assessments ranked by evidence-backed relevance. Optional company/skill/level filters."""
    return await coding_service.list_assessments(
        db,
        user,
        company_key=company_key,
        topic=topic,
        difficulty=difficulty,
    )


@router.get("/topics", response_model=TopicCatalogOut)
async def list_topics(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_roles(RoleCode.STUDENT.value)),
) -> TopicCatalogOut:
    """Topic browser for campus placement coding bank."""
    return await coding_practice.list_topics(db, user)


@router.get("/bank/problems", response_model=BankProblemListOut)
async def list_bank_problems(
    topic: str | None = Query(default=None, max_length=80),
    difficulty: str | None = Query(default=None, max_length=32),
    limit: int = Query(default=50, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_roles(RoleCode.STUDENT.value)),
) -> BankProblemListOut:
    """Browse published bank problems by topic/difficulty (student-safe cards)."""
    return await coding_practice.list_bank_problems(
        db, user, topic=topic, difficulty=difficulty, limit=limit
    )


@router.post("/practice/resolve", response_model=PracticeResolveOut)
async def resolve_practice(
    body: PracticeResolveRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_roles(RoleCode.STUDENT.value)),
) -> PracticeResolveOut:
    """
    Free-text topic + difficulty → practice assessment.
    Prefers published bank; optionally generates an original campus-placement problem
    through validation guardrails when the bank has no match.
    """
    return await coding_practice.resolve_practice(db, user, body)


@router.get("/assessments/{assessment_ref}", response_model=AssessmentSummaryOut)
async def get_assessment(
    assessment_ref: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_roles(RoleCode.STUDENT.value)),
) -> AssessmentSummaryOut:
    return await coding_service.get_assessment(db, user, assessment_ref)


@router.post("/assessments/{assessment_ref}/start", response_model=AttemptOut)
async def start_assessment(
    assessment_ref: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_roles(RoleCode.STUDENT.value)),
) -> AttemptOut:
    return await coding_service.start_assessment(db, user, assessment_ref)


@router.get("/attempts/{attempt_id}", response_model=AttemptOut)
async def get_attempt(
    attempt_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_roles(RoleCode.STUDENT.value)),
) -> AttemptOut:
    return await coding_service.get_attempt(db, user, attempt_id)


@router.get(
    "/attempts/{attempt_id}/problems/{problem_id}",
    response_model=AttemptProblemOut,
)
async def get_attempt_problem(
    attempt_id: int,
    problem_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_roles(RoleCode.STUDENT.value)),
) -> AttemptProblemOut:
    return await coding_service.get_attempt_problem(db, user, attempt_id, problem_id)


@router.put(
    "/attempts/{attempt_id}/problems/{problem_id}/draft",
    response_model=DraftOut,
)
async def upsert_draft(
    attempt_id: int,
    problem_id: int,
    body: DraftUpsertRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_roles(RoleCode.STUDENT.value)),
) -> DraftOut:
    return await coding_service.upsert_draft(db, user, attempt_id, problem_id, body)


@router.get(
    "/attempts/{attempt_id}/problems/{problem_id}/draft",
    response_model=DraftOut,
)
async def get_draft(
    attempt_id: int,
    problem_id: int,
    language: str = Query(..., min_length=1, max_length=32),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_roles(RoleCode.STUDENT.value)),
) -> DraftOut:
    return await coding_service.get_draft(db, user, attempt_id, problem_id, language)


@router.post("/runs", response_model=RunOut)
async def create_run(
    body: RunCreateRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_roles(RoleCode.STUDENT.value)),
) -> RunOut:
    """Enqueue public-test execution. Poll GET /runs/{id}. No OpenAI."""
    return await coding_service.enqueue_run(db, user, body)


@router.get("/runs/{run_id}", response_model=RunOut)
async def get_run(
    run_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_roles(RoleCode.STUDENT.value)),
) -> RunOut:
    return await coding_service.get_run(db, user, run_id)


@router.post("/submissions", response_model=SubmissionOut)
async def create_submission(
    body: SubmissionCreateRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_roles(RoleCode.STUDENT.value)),
) -> SubmissionOut:
    """Enqueue official evaluate (public + hidden). Score from tests only."""
    return await coding_service.enqueue_submission(db, user, body)


@router.get("/submissions", response_model=SubmissionListOut)
async def list_submissions(
    limit: int = Query(default=20, ge=1, le=50),
    company_key: str | None = Query(default=None, max_length=160),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_roles(RoleCode.STUDENT.value)),
) -> SubmissionListOut:
    """Past submissions for result revisit."""
    return await coding_service.list_submissions(
        db, user, limit=limit, company_key=company_key
    )


@router.get("/submissions/{submission_id}", response_model=SubmissionOut)
async def get_submission(
    submission_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_roles(RoleCode.STUDENT.value)),
) -> SubmissionOut:
    return await coding_service.get_submission(db, user, submission_id)


@router.get("/submissions/{submission_id}/analysis", response_model=AnalysisOut)
async def get_submission_analysis(
    submission_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_roles(RoleCode.STUDENT.value)),
) -> AnalysisOut:
    """Coaching analysis. Never replaces official_score."""
    return await coding_service.get_submission_analysis(db, user, submission_id)

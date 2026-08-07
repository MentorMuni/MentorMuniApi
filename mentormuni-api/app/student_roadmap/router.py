"""Student portal roadmap routes — baseline unlock + 90-day plan generation."""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, BackgroundTasks, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.deps import get_db, require_api_key, require_roles
from app.models.enums import RoleCode
from app.models.user import User
from app.services.llm import LLMService
from app.student_roadmap import service as roadmap_service
from app.student_roadmap.schemas import (
    AnalysisOut,
    AssessmentResultOut,
    CompleteStepRequest,
    GeneratedPlanOut,
    ProgressLearningTopicsOut,
    ProgressOut,
    RoadmapOut,
)

router = APIRouter(
    prefix="/student/roadmap",
    tags=["Student Roadmap"],
    dependencies=[Depends(require_api_key)],
)

_llm = LLMService()


@router.get("", response_model=RoadmapOut)
async def get_roadmap(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_roles(RoleCode.STUDENT.value)),
) -> RoadmapOut:
    return await roadmap_service.get_roadmap(db, user)


@router.post("/steps/{tool_code}/complete", response_model=RoadmapOut)
async def complete_step(
    tool_code: str,
    body: CompleteStepRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_roles(RoleCode.STUDENT.value)),
) -> RoadmapOut:
    return await roadmap_service.complete_step(db, user, tool_code, body)


@router.get("/analysis", response_model=AnalysisOut)
async def get_analysis(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_roles(RoleCode.STUDENT.value)),
) -> AnalysisOut:
    return await roadmap_service.get_analysis(db, user)


@router.get("/results", response_model=list[AssessmentResultOut])
async def get_results(
    tool_code: Optional[str] = Query(default=None),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_roles(RoleCode.STUDENT.value)),
) -> list[AssessmentResultOut]:
    return await roadmap_service.list_results(db, user, tool_code)


@router.post("/generate", response_model=GeneratedPlanOut)
async def generate_plan(
    background: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_roles(RoleCode.STUDENT.value)),
) -> GeneratedPlanOut:
    """Returns immediately with status=generating; the client polls GET /plan."""
    plan, plan_id = await roadmap_service.start_plan_generation(db, user)
    if plan_id is not None:
        background.add_task(roadmap_service.run_plan_generation, plan_id, _llm)
    return plan


@router.get("/plan", response_model=GeneratedPlanOut)
async def get_plan(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_roles(RoleCode.STUDENT.value)),
) -> GeneratedPlanOut:
    return await roadmap_service.get_latest_plan(db, user)


@router.get("/plan/{plan_id}", response_model=GeneratedPlanOut)
async def get_plan_by_id(
    plan_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_roles(RoleCode.STUDENT.value)),
) -> GeneratedPlanOut:
    return await roadmap_service.get_plan_by_id(db, user, plan_id)


@router.get("/progress", response_model=ProgressOut)
async def get_progress(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_roles(RoleCode.STUDENT.value)),
) -> ProgressOut:
    """Activity + strengths/weaknesses snapshot (no OpenAI call)."""
    return await roadmap_service.get_progress(db, user)


@router.post("/progress/learning-topics", response_model=ProgressLearningTopicsOut)
async def generate_progress_learning_topics(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_roles(RoleCode.STUDENT.value)),
) -> ProgressLearningTopicsOut:
    """OpenAI call: topics to learn for weak points + nearby areas (aptitude / skills / interview)."""
    return await roadmap_service.generate_progress_learning_topics(db, user, _llm)

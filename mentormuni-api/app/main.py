import sys
import os
import logging
import asyncio

# Ensure parent dir (mentormuni-api) is on path so 'app' package is found (Railway, etc.)
_here = os.path.dirname(os.path.abspath(__file__))
_root = os.path.dirname(_here)
if _root not in sys.path:
    sys.path.insert(0, _root)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)

from contextlib import asynccontextmanager
from typing import Optional

from fastapi import Depends, FastAPI, File, Form, HTTPException, Query, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from app.common.deps import require_api_key
from app.common.rate_limit import limiter

from app.schemas.ai import (
    SkillReadinessPlanRequest,
    SkillReadinessPlanResponse,
    AptitudeReadinessPlanRequest,
    AptitudeReadinessPlanResponse,
    InterviewReadinessPlanRequest,
    InterviewReadinessPlanResponse,
    EvaluateRequest,
    EvaluateResponse,
    VoiceInterviewSessionRequest,
    VoiceInterviewSessionResponse,
    VoiceInterviewAnalyzeRequest,
    VoiceInterviewAnalyzeResponse,
)
from app.schemas.inquiry import InquiryCreate
from app.schemas.interview_lead import InterviewReadyLeadCreate
from app.schemas.resume_ats import ResumeAtsResponse
from app.services import contact_storage, interview_lead_build, stats as stats_service
from app.services.guard_layer import GuardLayer
from app.services.llm import LLMService
from app.services.evaluator import EvaluatorService
from app.services.voice_interview import VoiceInterviewService
from app.services import resume_ats as resume_ats_service
from app.core.config import settings
from app.common.database import close_db, init_db
from app.auth.router import router as auth_router
from app.organizations.router import router as organizations_router
from app.organizations.departments_router import router as org_departments_router
from app.organizations.students_router import router as org_students_router
from app.organizations.notifications_router import router as org_notifications_router
from app.organizations.programs_router import router as org_programs_router
from app.organizations.hod_access_router import router as org_hod_access_router
from app.organizations.workspace_router import router as org_workspace_router
from app.organizations.upcoming_drives_router import router as org_upcoming_drives_router
from app.subscriptions.router import router as subscription_plans_router
from app.departments.router import router as departments_router
from app.users.router import router as users_router
from app.students.router import router as students_router
from app.notifications.router import router as notifications_router
from app.dashboard.router import router as dashboard_router
from app.platform.router import router as platform_router
from app.student_roadmap.router import router as student_roadmap_router
from app.student_intelligence.router import router as student_intelligence_router
from app.personal_mentor.router import router as personal_mentor_router
from app.know_my_fear.router_v2 import router as know_my_fear_router
from app.know_my_fear.router_v2 import legacy_router as know_my_fear_legacy_router
from app.know_my_fear.intervention_router import router as intervention_router
from app.know_my_fear.intervention_router import legacy_router as intervention_legacy_router
from app.know_my_fear.notification_dispatcher import (
    start_notification_dispatcher,
    stop_notification_dispatcher,
)
from app.org_performance.router import router as org_performance_router
from app.org_performance.router import ai_router as org_performance_ai_router
from app.student_company_prep.router import router as student_company_prep_router
from app.company_intelligence.router import router as company_intelligence_router
from app.coding.router import router as coding_router
from app.platform_support.router import router as support_tenant_router
from app.platform_support.platform_router import router as support_platform_router
from app.whiteboard.router import router as whiteboard_router
from app.aptitude_arcade.router import router as aptitude_arcade_router
from app.media.router import router as media_router


@asynccontextmanager
async def lifespan(_app: FastAPI):
    """Warm DB engine on startup; run Fear → Fearless notification dispatcher; dispose on shutdown."""
    await init_db()
    start_notification_dispatcher()
    yield
    await stop_notification_dispatcher()
    await close_db()


app = FastAPI(title="MentorMuni API", version="1.0.0", lifespan=lifespan)

# Rate limiter: shared instance (routers import from app.common.rate_limit)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    # Apex + college subdomains + Vercel previews + local Vite (incl. *.localhost tenants).
    allow_origin_regex=(
        r"https://([a-z0-9-]+\.)?mentormuni\.com|"
        r"https://.*\.vercel\.app|"
        r"http://((?:[a-z0-9-]+\.)*)?(localhost|127\.0\.0\.1):\d+"
    ),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Org Portal Track A (API key + JWT where required)
app.include_router(auth_router)
# Register before /organizations/{id} so static segments are not parsed as org ids
app.include_router(org_departments_router)
app.include_router(org_students_router)
app.include_router(org_notifications_router)
app.include_router(org_programs_router)
app.include_router(org_workspace_router)
app.include_router(org_hod_access_router)
app.include_router(org_upcoming_drives_router)
app.include_router(organizations_router)
app.include_router(subscription_plans_router)
app.include_router(departments_router)
app.include_router(users_router)
app.include_router(students_router)
app.include_router(notifications_router)
app.include_router(dashboard_router)
app.include_router(student_roadmap_router)
app.include_router(student_intelligence_router)
app.include_router(personal_mentor_router)
app.include_router(know_my_fear_router)
app.include_router(know_my_fear_legacy_router)
app.include_router(intervention_router)
app.include_router(intervention_legacy_router)
app.include_router(org_performance_router)
app.include_router(org_performance_ai_router)
app.include_router(student_company_prep_router)
app.include_router(company_intelligence_router)
app.include_router(coding_router)
app.include_router(support_tenant_router)
app.include_router(whiteboard_router)
app.include_router(aptitude_arcade_router)
# Public media (org logos) — no API key; usable from <img src>
app.include_router(media_router)
# MentorMuni Platform Admin portal (tenant provisioning only)
app.include_router(platform_router)
app.include_router(support_platform_router)

guard_layer = GuardLayer(timeout=settings.llm_timeout_seconds)
logger = logging.getLogger(__name__)
llm_service = LLMService()
evaluator_service = EvaluatorService()
voice_interview_service = VoiceInterviewService()


@app.get("/health")
async def health_check():
    """Root-level health check for Railway, load balancers, and orchestrators."""
    from datetime import datetime, timezone
    return {
        "status": "healthy",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "version": "1.0.0",
    }


@app.post(
    "/interview-ready/skill-readiness/plan",
    response_model=SkillReadinessPlanResponse,
    responses={429: {"description": "Rate limit exceeded"}},
    summary="Skill readiness plan (stack-only quiz: MC, scenario, code MCQ + explanations)",
)
@limiter.limit("100/minute")
async def skill_readiness_plan(request: Request, body: SkillReadinessPlanRequest):
    try:
        if settings.skip_skill_validation:
            # OPTIMIZATION: Skip validation (2-3s saved) - let generation LLM handle invalid skills
            evaluation_plan = await guard_layer.run_with_timeout(
                llm_service.generate_skill_readiness_plan(body)
            )
        else:
            # Original: Parallelize skill validation + plan generation
            async def validate_skill():
                is_valid, error_msg = await llm_service.validate_primary_skill(body.primary_skill)
                if not is_valid:
                    detail = error_msg if error_msg else "Please enter a valid technical skill (e.g. React, .NET, Python)"
                    if not detail.startswith("Please"):
                        detail = f"Please enter a valid technical skill. {detail}"
                    raise HTTPException(status_code=422, detail=detail)
                return True

            async def generate_plan():
                return await guard_layer.run_with_timeout(
                    llm_service.generate_skill_readiness_plan(body)
                )

            # Run validation and generation in parallel
            _, evaluation_plan = await asyncio.gather(validate_skill(), generate_plan())
        
        rec = interview_lead_build.lead_from_skill_readiness(
            email=body.email,
            phone=body.phone,
            user_type_canonical=body.user_type,
            primary_skill=body.primary_skill,
            target_role=body.target_role,
            experience_years=body.experience_years or 0,
        )
        if rec:
            stats_service.append_interview_ready_lead(rec)
        return SkillReadinessPlanResponse(evaluation_plan=evaluation_plan)
    except HTTPException:
        raise
    except TimeoutError as e:
        raise HTTPException(status_code=504, detail=str(e))
    except Exception:
        raise HTTPException(status_code=500, detail="Failed to generate skill readiness plan. Please try again.")


@app.post(
    "/interview-ready/interview-readiness/plan",
    response_model=InterviewReadinessPlanResponse,
    responses={429: {"description": "Rate limit exceeded"}},
    summary="Interview readiness plan (Yes/No + multiple choice, holistic)",
)
@limiter.limit("100/minute")
async def interview_readiness_plan(request: Request, body: InterviewReadinessPlanRequest):
    try:
        if settings.skip_skill_validation:
            # OPTIMIZATION: Skip validation (2-3s saved)
            evaluation_plan = await guard_layer.run_with_timeout(
                llm_service.generate_interview_readiness_plan(body)
            )
        else:
            # Original: Parallelize skill validation + plan generation
            async def validate_skill():
                is_valid, error_msg = await llm_service.validate_primary_skill(body.primary_skill)
                if not is_valid:
                    detail = error_msg if error_msg else "Please enter a valid technical skill (e.g. React, .NET, Python)"
                    if not detail.startswith("Please"):
                        detail = f"Please enter a valid technical skill. {detail}"
                    raise HTTPException(status_code=422, detail=detail)
                return True

            async def generate_plan():
                return await guard_layer.run_with_timeout(
                    llm_service.generate_interview_readiness_plan(body)
                )

            # Run validation and generation in parallel
            _, evaluation_plan = await asyncio.gather(validate_skill(), generate_plan())
        
        rec = interview_lead_build.lead_from_interview_readiness(body)
        if rec:
            stats_service.append_interview_ready_lead(rec)
        return InterviewReadinessPlanResponse(evaluation_plan=evaluation_plan)
    except HTTPException:
        raise
    except TimeoutError as e:
        raise HTTPException(status_code=504, detail=str(e))
    except Exception:
        raise HTTPException(status_code=500, detail="Failed to generate interview readiness plan. Please try again.")


@app.post(
    "/interview-ready/aptitude-readiness/plan",
    response_model=AptitudeReadinessPlanResponse,
    responses={429: {"description": "Rate limit exceeded"}},
    summary="Aptitude readiness plan (adaptive count/level; quant/logical/verbal + non-verbal mix)",
)
@limiter.limit("100/minute")
async def aptitude_readiness_plan(request: Request, body: AptitudeReadinessPlanRequest):
    try:
        # Timeout + retries are applied inside generate_aptitude_readiness_plan (avoid nested wait_for).
        evaluation_plan = await llm_service.generate_aptitude_readiness_plan(body)
        rec = interview_lead_build.lead_from_skill_readiness(
            email=body.email,
            phone=body.phone,
            user_type_canonical=body.user_type,
            primary_skill=body.primary_skill,
            target_role=body.target_role,
            experience_years=body.experience_years or 0,
        )
        if rec:
            stats_service.append_interview_ready_lead(rec)
        return AptitudeReadinessPlanResponse(evaluation_plan=evaluation_plan)
    except HTTPException:
        raise
    except TimeoutError as e:
        raise HTTPException(status_code=504, detail=str(e))
    except Exception:
        logger.exception("aptitude_readiness_plan failed")
        raise HTTPException(status_code=500, detail="Failed to generate aptitude readiness plan. Please try again.")


@app.post(
    "/interview-ready/voice-interview/session",
    response_model=VoiceInterviewSessionResponse,
    responses={
        429: {"description": "Rate limit exceeded"},
        502: {"description": "OpenAI Realtime session creation failed"},
    },
    summary="Mint OpenAI Realtime ephemeral key for live MNC-style voice interview",
    dependencies=[Depends(require_api_key)],
)
@limiter.limit("100/minute")
async def voice_interview_session(request: Request, body: VoiceInterviewSessionRequest):
    """
    Creates an OpenAI Realtime ephemeral client secret for browser WebRTC voice interviews.

    Requires X-API-Key. Send `interview_focus` in the body (e.g. Java, C++, projects only).
    Model is server-fixed (client model override ignored).
    """
    try:
        return await voice_interview_service.create_session(body)
    except RuntimeError as e:
        raise HTTPException(status_code=502, detail=str(e)) from e
    except Exception:
        logger.exception("voice_interview_session failed")
        raise HTTPException(
            status_code=500,
            detail="Failed to create voice interview session. Please try again.",
        )


@app.post(
    "/interview-ready/voice-interview/analyze",
    response_model=VoiceInterviewAnalyzeResponse,
    responses={
        429: {"description": "Rate limit exceeded"},
        502: {"description": "Analysis model failed"},
    },
    summary="Score a completed voice interview transcript (technical + communication + study plan)",
    dependencies=[Depends(require_api_key)],
)
@limiter.limit("100/minute")
async def voice_interview_analyze(request: Request, body: VoiceInterviewAnalyzeRequest):
    """
    After the live Realtime interview ends, POST the captured transcript turns.
    Requires X-API-Key. Uses a GPT analysis model (not Realtime) for structured scores.
    """
    try:
        return await guard_layer.run_with_timeout(
            voice_interview_service.analyze_interview(body)
        )
    except TimeoutError as e:
        raise HTTPException(status_code=504, detail=str(e)) from e
    except RuntimeError as e:
        raise HTTPException(status_code=502, detail=str(e)) from e
    except Exception:
        logger.exception("voice_interview_analyze failed")
        raise HTTPException(
            status_code=500,
            detail="Failed to analyze voice interview. Please try again.",
        )


@app.post(
    "/api/resume/ats",
    response_model=ResumeAtsResponse,
    responses={
        413: {"description": "File too large"},
        429: {"description": "Rate limit exceeded"},
    },
)
@limiter.limit("100/minute")
async def resume_ats(
    request: Request,
    file: UploadFile = File(...),
    target_role: str = Form(...),
    candidate_type: Optional[str] = Form(None),
    experience_years: Optional[int] = Form(None),
    job_description: Optional[str] = Form(None),
):
    """
    Upload a resume (PDF, DOC, or DOCX) and receive ATS-style scores and keyword feedback.
    Multipart form fields: `file`, `target_role`; optional `candidate_type`, `experience_years`, `job_description`.
    Scores and keyword lists are heuristic; summary/fixes/strengths are enriched via OpenAI when enabled.
    """
    tr = (target_role or "").strip()
    if not tr:
        raise HTTPException(status_code=422, detail="target_role is required.")

    ct = (candidate_type or "").strip() or None
    if ct and ct.lower().replace(" ", "_") not in (
        "college_student",
        "experienced",
        "fresher",
        "student",
    ):
        raise HTTPException(
            status_code=422,
            detail="candidate_type must be college_student, experienced, or fresher.",
        )
    if experience_years is not None and (experience_years < 0 or experience_years > 50):
        raise HTTPException(status_code=422, detail="experience_years must be between 0 and 50.")

    jd = (job_description or "").strip() or None

    raw = await file.read()
    if len(raw) > resume_ats_service.MAX_FILE_BYTES:
        raise HTTPException(
            status_code=413,
            detail=f"File too large. Maximum size is {resume_ats_service.MAX_FILE_BYTES // (1024 * 1024)} MB.",
        )

    name = (file.filename or "resume").strip() or "resume"
    try:
        text = resume_ats_service.extract_text(name, raw)
        payload = resume_ats_service.analyze_resume(
            text,
            tr,
            candidate_type=ct,
            experience_years=experience_years,
            job_description=jd,
        )
        payload = await resume_ats_service.enrich_analysis_with_llm(payload, text, tr, job_description=jd)
        return ResumeAtsResponse(**payload)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e)) from e
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(
            status_code=500,
            detail="Could not analyze this resume. Please try again or use a different file.",
        )


@app.post("/api/inquiries")
@limiter.limit("100/minute")
async def create_inquiry(request: Request, body: InquiryCreate):
    """Waitlist + contact submissions (intent-branched); stored as JSONL."""
    try:
        contact_storage.store_submission(body.model_dump(mode="json", exclude_none=False))
        return {"status": "ok", "message": "Thank you! We'll get back to you."}
    except Exception:
        raise HTTPException(status_code=500, detail="Could not save your details. Please try again.")


@app.post(
    "/interview-ready/evaluate",
    response_model=EvaluateResponse,
    responses={429: {"description": "Rate limit exceeded"}},
)
@limiter.limit("100/minute")
async def evaluate_readiness(request: Request, body: EvaluateRequest):
    try:
        evaluation_result = await evaluator_service.evaluate_readiness(body)
        return EvaluateResponse(**evaluation_result)
    except Exception as e:
        raise HTTPException(status_code=500, detail="Evaluation failed. Please try again.")


from slowapi.middleware import SlowAPIMiddleware

app.add_middleware(SlowAPIMiddleware)


# ---- Admin endpoints (backend only, no auth) ----

@app.get("/admin/submissions")
async def admin_submissions(limit: int = 100):
    """Return inquiry submissions (waitlist + contact JSONL)."""
    data = contact_storage.get_submissions(limit=limit)
    return {"count": len(data), "submissions": data}


@app.get("/admin/leads")
async def admin_leads(
    limit: Optional[int] = Query(
        default=None,
        ge=1,
        le=500_000,
        description="Optional max number of most recent leads. Omit to return all rows in the file.",
    ),
):
    """Return Interview Ready leads (full JSON per row, newest first). POST /admin/leads appends the same shape."""
    data = stats_service.get_leads(limit=limit)
    return {"count": len(data), "leads": data}


@app.post("/admin/leads")
@limiter.limit("100/minute")
async def admin_create_lead(request: Request, body: InterviewReadyLeadCreate):
    """Append a lead row from the client (same shape as server-side plan capture)."""
    stats_service.append_interview_ready_lead(body.to_storage_dict())
    return {"status": "ok"}

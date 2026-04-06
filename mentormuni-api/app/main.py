import sys
import os
import logging

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

from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from app.schemas.ai import (
    PlanRequest,
    PlanResponse,
    SkillReadinessPlanRequest,
    SkillReadinessPlanResponse,
    InterviewReadinessPlanRequest,
    InterviewReadinessPlanResponse,
    EvaluateRequest,
    EvaluateResponse,
)
from app.schemas.inquiry import InquiryCreate
from app.schemas.interview_lead import InterviewReadyLeadCreate
from app.schemas.resume_ats import ResumeAtsResponse
from app.services import contact_storage, interview_lead_build, stats as stats_service
from app.services.guard_layer import GuardLayer
from app.services.llm import LLMService
from app.services.evaluator import EvaluatorService
from app.services import resume_ats as resume_ats_service

app = FastAPI(title="MentorMuni API", version="1.0.0")

# Rate limiter: 10k users = ~20 req/min/IP for plan (LLM), 60/min for evaluate
limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

guard_layer = GuardLayer(timeout=30)
llm_service = LLMService()
evaluator_service = EvaluatorService()

@app.get("/")
async def root():
    return {"message": "Welcome to MentorMuni API!"}


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
    "/interview-ready/plan",
    response_model=PlanResponse,
    responses={429: {"description": "Rate limit exceeded"}},
    summary="Legacy plan (15 Yes/No questions only)",
)
@limiter.limit("20/minute")
async def generate_plan(request: Request, body: PlanRequest):
    try:
        # Validate primary_skill via OpenAI before generating plan
        is_valid, error_msg = await llm_service.validate_primary_skill(body.primary_skill)
        if not is_valid:
            detail = error_msg if error_msg else "Please enter a valid technical skill (e.g. React, .NET, Python)"
            if not detail.startswith("Please"):
                detail = f"Please enter a valid technical skill. {detail}"
            raise HTTPException(status_code=422, detail=detail)
        evaluation_plan = await guard_layer.run_with_timeout(
            llm_service.generate_evaluation_plan(body)
        )
        rec = interview_lead_build.lead_from_legacy_plan(
            email=body.email,
            phone=body.phone,
            user_type_canonical=body.user_type,
            primary_skill=body.primary_skill,
            target_role=body.target_role,
            experience_years=body.experience_years or 0,
        )
        if rec:
            stats_service.append_interview_ready_lead(rec)
        return PlanResponse(evaluation_plan=evaluation_plan)
    except HTTPException:
        raise
    except TimeoutError as e:
        raise HTTPException(status_code=504, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to generate plan. Please try again.")


@app.post(
    "/interview-ready/skill-readiness/plan",
    response_model=SkillReadinessPlanResponse,
    responses={429: {"description": "Rate limit exceeded"}},
    summary="Skill readiness plan (rigorous stack-only quiz: yes/no, MC, scenario, code MCQ + explanations)",
)
@limiter.limit("20/minute")
async def skill_readiness_plan(request: Request, body: SkillReadinessPlanRequest):
    try:
        is_valid, error_msg = await llm_service.validate_primary_skill(body.primary_skill)
        if not is_valid:
            detail = error_msg if error_msg else "Please enter a valid technical skill (e.g. React, .NET, Python)"
            if not detail.startswith("Please"):
                detail = f"Please enter a valid technical skill. {detail}"
            raise HTTPException(status_code=422, detail=detail)
        evaluation_plan = await guard_layer.run_with_timeout(
            llm_service.generate_skill_readiness_plan(body)
        )
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
@limiter.limit("20/minute")
async def interview_readiness_plan(request: Request, body: InterviewReadinessPlanRequest):
    try:
        is_valid, error_msg = await llm_service.validate_primary_skill(body.primary_skill)
        if not is_valid:
            detail = error_msg if error_msg else "Please enter a valid technical skill (e.g. React, .NET, Python)"
            if not detail.startswith("Please"):
                detail = f"Please enter a valid technical skill. {detail}"
            raise HTTPException(status_code=422, detail=detail)
        evaluation_plan = await guard_layer.run_with_timeout(
            llm_service.generate_interview_readiness_plan(body)
        )
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
    "/api/resume/ats",
    response_model=ResumeAtsResponse,
    responses={
        413: {"description": "File too large"},
        429: {"description": "Rate limit exceeded"},
    },
)
@limiter.limit("30/minute")
async def resume_ats(
    request: Request,
    file: UploadFile = File(...),
    target_role: str = Form(...),
):
    """
    Upload a resume (PDF, DOC, or DOCX) and receive ATS-style scores and keyword feedback.
    Multipart form fields: `file`, `target_role`.
    """
    tr = (target_role or "").strip()
    if not tr:
        raise HTTPException(status_code=422, detail="target_role is required.")

    raw = await file.read()
    if len(raw) > resume_ats_service.MAX_FILE_BYTES:
        raise HTTPException(
            status_code=413,
            detail=f"File too large. Maximum size is {resume_ats_service.MAX_FILE_BYTES // (1024 * 1024)} MB.",
        )

    name = (file.filename or "resume").strip() or "resume"
    try:
        text = resume_ats_service.extract_text(name, raw)
        payload = resume_ats_service.analyze_resume(text, tr)
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
@limiter.limit("10/minute")
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
@limiter.limit("60/minute")
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
async def admin_leads(limit: int = 100):
    """Return Interview Ready leads (JSONL lines, newest first)."""
    data = stats_service.get_leads(limit=limit)
    return {"count": len(data), "leads": data}


@app.post("/admin/leads")
@limiter.limit("60/minute")
async def admin_create_lead(request: Request, body: InterviewReadyLeadCreate):
    """Append a lead row from the client (same shape as server-side plan capture)."""
    stats_service.append_interview_ready_lead(body.to_storage_dict())
    return {"status": "ok"}

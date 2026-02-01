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

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from app.api.v1.routes import health, ai
from app.schemas.ai import PlanRequest, PlanResponse, EvaluateRequest, EvaluateResponse
from app.services.guard_layer import GuardLayer
from app.services.llm import LLMService
from app.services.evaluator import EvaluatorService

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

app.include_router(health.router, prefix="/api/v1/health", tags=["Health"])
app.include_router(ai.router, prefix="/api/v1/ai", tags=["AI"])


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
)
@limiter.limit("20/minute")
async def generate_plan(request: Request, body: PlanRequest):
    try:
        evaluation_plan = await guard_layer.run_with_timeout(
            llm_service.generate_evaluation_plan(body)
        )
        return PlanResponse(evaluation_plan=evaluation_plan)
    except TimeoutError as e:
        raise HTTPException(status_code=504, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to generate plan. Please try again.")


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

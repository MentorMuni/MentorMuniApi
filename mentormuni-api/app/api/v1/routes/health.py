from fastapi import APIRouter
from datetime import datetime, timezone

router = APIRouter()


@router.get("/ping")
async def ping():
    """Simple ping-pong for quick liveness check."""
    return {"message": "pong"}


@router.get("")
@router.get("/")
async def health():
    """Full health check for load balancers, Railway, and orchestrators."""
    return {
        "status": "healthy",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "version": "1.0.0",
    }
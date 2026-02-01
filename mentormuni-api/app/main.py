import sys
import os

# Add the mentormuni-api directory to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from app.api.v1.routes import health, ai

app = FastAPI()

# Add middleware for CORS and trusted hosts
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])
app.add_middleware(TrustedHostMiddleware, allowed_hosts=["*"])

# Add middleware for logging
@app.middleware("http")
async def log_requests(request, call_next):
    response = await call_next(request)
    print(f"{request.method} {request.url} - {response.status_code}")
    return response

# Include routers
app.include_router(health.router, prefix="/api/v1/health", tags=["Health"])
app.include_router(ai.router, prefix="/api/v1/ai", tags=["AI"])

@app.get("/")
async def root():
    return {"message": "Welcome to MentorMuni API!"}
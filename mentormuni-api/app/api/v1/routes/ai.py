from fastapi import APIRouter, HTTPException
from app.schemas.ai import AIRequest, AIResponse
from app.services.openai_service import OpenAIService

router = APIRouter()

@router.post("/generate", response_model=AIResponse)
async def generate_text(request: AIRequest):
    try:
        response = await OpenAIService.generate_text(request.prompt, request.use_case)
        return AIResponse(output=response)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
from typing import Optional
from openai import AsyncOpenAI
from app.core.config import settings

_client: Optional[AsyncOpenAI] = None


def _get_client() -> AsyncOpenAI:
    global _client
    if _client is None:
        _client = AsyncOpenAI(api_key=settings.openai_api_key)
    return _client


class OpenAIService:
    @staticmethod
    async def generate_text(prompt: str, use_case: str) -> str:
        response = await _get_client().chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": f"You are an assistant specialized in {use_case}."},
                {"role": "user", "content": prompt},
            ],
            max_tokens=150,
        )
        return response.choices[0].message.content.strip()

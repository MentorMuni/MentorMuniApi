from openai import OpenAI
from app.core.config import settings

client = OpenAI(api_key=settings.openai_api_key)

class OpenAIService:
    @staticmethod
    async def generate_text(prompt: str, use_case: str) -> str:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": f"You are an assistant specialized in {use_case}."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=150
        )

        return response.choices[0].message.content.strip()

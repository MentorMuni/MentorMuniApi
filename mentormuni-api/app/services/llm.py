import json
import logging
import re
from openai import AsyncOpenAI
from app.core.config import settings
from app.services.guard_layer import GuardLayer

logger = logging.getLogger("llm_service")

# LLM timeout in seconds (for 10k users, avoid long-running requests)
LLM_TIMEOUT = 30
MAX_TOKENS_PLAN = 500


class LLMService:
    def __init__(self):
        self._client = AsyncOpenAI(api_key=settings.openai_api_key)
        self.guard_layer = GuardLayer(timeout=LLM_TIMEOUT)

    async def generate_evaluation_plan(self, request) -> list[str]:
        prompt = f"""You are an expert interview evaluator. Based on the following user profile, generate exactly 8-10 core topics that are YES/NO answerable for interview preparation.

User Profile:
- User Type: {request.user_type}
- Experience: {request.experience_years} years
- Primary Skill: {request.primary_skill}
- Target Role: {request.target_role}

Return ONLY a JSON array of topic strings. No other text. Example: ["Topic 1", "Topic 2", ...]"""

        async def call_openai():
            response = await self._client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=MAX_TOKENS_PLAN,
            )
            content = response.choices[0].message.content or ""
            usage = getattr(response, "usage", None)
            if usage:
                tokens = getattr(usage, "total_tokens", 0) or 0
                logger.info("LLM tokens used: %d (request)", tokens)
            return self._parse_topics(content)

        return await self.guard_layer.run_with_timeout(
            self.guard_layer.retry_with_fallback(call_openai)
        )

    def _parse_topics(self, content: str) -> list[str]:
        """Parse LLM response into list of topic strings. Deterministic fallback."""
        content = content.strip()
        # Try JSON array first
        json_match = re.search(r"\[[\s\S]*\]", content)
        if json_match:
            try:
                topics = json.loads(json_match.group())
                if isinstance(topics, list) and all(isinstance(t, str) for t in topics):
                    return [t.strip() for t in topics if t.strip()][:10]
            except json.JSONDecodeError:
                pass
        # Fallback: split by newlines or numbered list
        lines = [
            re.sub(r"^\s*\d+[\.\)]\s*", "", line).strip()
            for line in content.split("\n")
            if line.strip()
        ]
        return [l for l in lines if len(l) > 2][:10] if lines else ["Interview fundamentals"]

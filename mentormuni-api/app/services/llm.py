import json
import logging
import re
from openai import AsyncOpenAI
from app.core.config import settings
from app.services.guard_layer import GuardLayer

logger = logging.getLogger("llm_service")

# LLM timeout in seconds (for 10k users, avoid long-running requests)
LLM_TIMEOUT = 30
MAX_TOKENS_PLAN = 1200


class LLMService:
    def __init__(self):
        self._client = AsyncOpenAI(api_key=settings.openai_api_key)
        self.guard_layer = GuardLayer(timeout=LLM_TIMEOUT)

    async def generate_evaluation_plan(self, request) -> list[dict]:
        """Returns list of {question, correct_answer} where correct_answer is 'Yes' or 'No'."""
        prompt = f"""You are a senior technical interviewer at a top product company.

Your task:
Generate EXACTLY 15 HIGH-QUALITY YES/NO interview questions that realistically assess interview readiness.

These questions MUST:
- Feel like real interviewer screening questions
- Require thinking, not guessing
- Include tricky edge cases and misconceptions
- Prevent "blind Yes" answers
- Mix difficulty: medium → hard → tricky
- Have ONLY ONE correct answer: Yes or No

User Profile:
- User Type: {request.user_type}
- Experience: {request.experience_years} years
- Primary Skill: {request.primary_skill}
- Target Role: {request.target_role}

-----------------------------------------
QUESTION STRUCTURE (MANDATORY)
-----------------------------------------

Return questions in THIS ORDER:

### Section 1: Capability Gate (5 questions)
Purpose: Check if candidate truly understands core responsibilities.

Style:
- "Can you explain / design / reason about…"
- These are NOT trivial
- Expert SHOULD say "Yes", but ONLY if genuinely prepared

Examples:
- "Can you explain how dependency injection improves testability in large systems?"
- "Can you reason about when NOT to use async code?"

Correct answer: usually "Yes"

-----------------------------------------

### Section 2: Concept Validation (5 questions)
Purpose: Validate depth, not surface knowledge.

Style:
- Precise technical statements
- Require understanding of internals
- No obvious textbook wording

Examples:
- "In .NET, scoped services are shared across threads in the same request. Yes or No?"
- "React state updates are always synchronous. Yes or No?"

Mix of Yes and No REQUIRED.

-----------------------------------------

### Section 3: Interview Traps & Edge Cases (5 questions)
Purpose: Separate interview-ready from resume-ready.

Style:
- Common misconceptions
- Edge conditions
- Real interview traps
- Even experienced devs get these wrong

Examples:
- "Adding an index always improves query performance. Yes or No?"
- "Using Singleton guarantees thread safety. Yes or No?"
- "Microservices always scale better than monoliths. Yes or No?"

Most answers here should be "No".

-----------------------------------------
STRICT RULES (DO NOT VIOLATE)
-----------------------------------------

1. NO basic or trivia questions
2. NO opinion-based questions
3. NO obvious answers
4. NO repeating concepts
5. NO more than 60% "Yes" answers total
6. Questions MUST require reasoning, not memory
7. Questions MUST feel like real interview questions

-----------------------------------------
OUTPUT FORMAT (STRICT)
-----------------------------------------

Return ONLY a JSON array of exactly 15 objects.

Each object:
{{
  "question": "string",
  "correct_answer": "Yes" | "No"
}}

No explanation.
No markdown.
No extra text.
-----------------------------------------"""

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
            return self._parse_plan(content)

        return await self.guard_layer.run_with_timeout(
            self.guard_layer.retry_with_fallback(call_openai)
        )

    def _parse_plan(self, content: str) -> list[dict]:
        """Parse LLM response into list of {question, correct_answer}. Deterministic fallback."""
        content = content.strip()
        json_match = re.search(r"\[[\s\S]*\]", content)
        if json_match:
            try:
                items = json.loads(json_match.group())
                if not isinstance(items, list):
                    raise ValueError("not a list")
                out = []
                for i, x in enumerate(items[:15]):
                    if isinstance(x, dict) and "question" in x and "correct_answer" in x:
                        q = str(x["question"]).strip()
                        raw = str(x["correct_answer"]).strip().lower()
                        if raw == "yes":
                            a = "Yes"
                        elif raw == "no":
                            a = "No"
                        else:
                            continue
                        if q:
                            out.append({"question": q, "correct_answer": a})
                    elif isinstance(x, str) and x.strip():
                        out.append({"question": x.strip(), "correct_answer": "Yes"})
                if out:
                    return out
            except (json.JSONDecodeError, ValueError):
                pass
        return [{"question": "Interview fundamentals", "correct_answer": "Yes"}]

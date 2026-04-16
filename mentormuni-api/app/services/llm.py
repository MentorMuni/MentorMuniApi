from __future__ import annotations

import json
import logging
import re
from typing import List, Optional, Tuple
from openai import AsyncOpenAI
from app.core.config import settings as app_settings
from app.services.guard_layer import GuardLayer
from app.services.skill_readiness_prompt import render_skill_readiness_prompt
from app.services.interview_readiness_prompt import render_interview_readiness_prompt
from app.services.aptitude_readiness_prompt import render_aptitude_readiness_prompt
from app.schemas.ai import InterviewReadinessPlanRequest

logger = logging.getLogger("llm_service")

MAX_TOKENS_LEGACY_PLAN = 1500
MAX_TOKENS_MIXED_PLAN = 3200
MAX_TOKENS_INTERVIEW_READINESS_PLAN = 14_000
MAX_TOKENS_SKILL_READINESS_PLAN = 8000
MAX_TOKENS_VALIDATE = 20
PLAN_QUESTION_COUNT = 15


class LLMService:
    def __init__(self):
        self._client = AsyncOpenAI(api_key=app_settings.openai_api_key)
        self.guard_layer = GuardLayer(timeout=app_settings.llm_timeout_seconds)

    async def validate_primary_skill(self, skill: str) -> Tuple[bool, str]:
        """
        Use OpenAI to check if skill is a valid technical skill.
        Returns (is_valid, error_message). If valid, message is empty.
        """
        prompt = f"""Is "{skill}" a valid technical skill, programming language, framework, tool, or tech domain that developers/engineers would use for interview preparation?

Answer with ONLY: YES or NO
If NO, also add a brief reason after a pipe, e.g. NO|Not a technical skill
If YES, respond with just: YES"""

        try:
            response = await self.guard_layer.run_with_timeout(
                self._client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[{"role": "user", "content": prompt}],
                    max_tokens=MAX_TOKENS_VALIDATE,
                )
            )
            content = (response.choices[0].message.content or "").strip().upper()
            if content.startswith("YES"):
                return True, ""
            if content.startswith("NO"):
                reason = content.split("|", 1)[1].strip() if "|" in content else "Not a recognized technical skill"
                return False, reason
            return False, "Could not validate. Please enter a technical skill like React, .NET, or Python."
        except Exception as e:
            logger.warning("Skill validation failed: %s", e)
            return True, ""  # On error, allow (don't block due to API failure)

    async def generate_evaluation_plan(self, request) -> list[dict]:
        """Legacy /interview-ready/plan: 15 Yes/No only (LegacyPlanQuestionItem)."""
        prompt = f"""You are a senior technical interviewer at a top product company.

Your task:
Generate EXACTLY {PLAN_QUESTION_COUNT} HIGH-QUALITY YES/NO interview questions that realistically assess interview readiness.

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

Correct answer: usually "Yes"

-----------------------------------------

### Section 2: Concept Validation (5 questions)
Purpose: Validate depth, not surface knowledge.

Style:
- Precise technical statements
- Require understanding of internals
- No obvious textbook wording

Mix of Yes and No REQUIRED.

-----------------------------------------

### Section 3: Interview Traps & Edge Cases (5 questions)
Purpose: Separate interview-ready from resume-ready.

Style:
- Common misconceptions
- Edge conditions
- Real interview traps
- Even experienced devs get these wrong

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

Return ONLY a JSON array of exactly {PLAN_QUESTION_COUNT} objects.

Each object:
{{
  "question": "string",
  "correct_answer": "Yes" | "No",
  "study_topic": "string"
}}

study_topic: SHORT topic name for study recommendations (2-5 words). NOT the question text.

No explanation.
No markdown.
No extra text.
-----------------------------------------"""

        async def call_openai():
            response = await self._client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=MAX_TOKENS_LEGACY_PLAN,
            )
            content = response.choices[0].message.content or ""
            usage = getattr(response, "usage", None)
            if usage:
                tokens = getattr(usage, "total_tokens", 0) or 0
                logger.info("LLM tokens used: %d (legacy plan)", tokens)
            return self._parse_legacy_plan(content)

        return await self.guard_layer.run_with_timeout(
            self.guard_layer.retry_with_fallback(call_openai)
        )

    async def generate_skill_readiness_plan(self, request) -> list[dict]:
        """Skill readiness: rigorous boundary, yes_no + MC + scenario + code_mcq + explanations."""
        prompt = render_skill_readiness_prompt(
            user_type=request.user_type,
            experience_years=request.experience_years,
            primary_skill=request.primary_skill,
            target_role=request.target_role or f"{request.primary_skill} Developer",
            target_company_type=request.target_company_type,
        )

        async def call_openai():
            response = await self._client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=MAX_TOKENS_SKILL_READINESS_PLAN,
            )
            content = response.choices[0].message.content or ""
            usage = getattr(response, "usage", None)
            if usage:
                tokens = getattr(usage, "total_tokens", 0) or 0
                logger.info("LLM tokens used: %d (skill readiness plan)", tokens)
            return self._parse_skill_readiness_plan(content)

        return await self.guard_layer.run_with_timeout(
            self.guard_layer.retry_with_fallback(call_openai)
        )

    @staticmethod
    def _explanation_or_default(raw) -> str:
        e = str(raw).strip() if raw is not None else ""
        return e if e else (
            "Compare your answer to the official behavior of this skill; the key is specificity to this stack."
        )

    def _parse_skill_readiness_plan(self, content: str) -> list[dict]:
        """Parse skill readiness JSON: yes_no | multiple_choice | scenario | code_mcq with explanation."""
        content = content.strip()
        json_match = re.search(r"\[[\s\S]*\]", content)
        if json_match:
            try:
                items = json.loads(json_match.group())
                if not isinstance(items, list):
                    raise ValueError("not a list")
                out: List[dict] = []
                # Consume all array items until we have 15 valid (model may send extras if some rows are bad).
                for x in items:
                    if len(out) >= PLAN_QUESTION_COUNT:
                        break
                    if not isinstance(x, dict) or "question" not in x:
                        continue
                    q = str(x["question"]).strip()
                    if not q:
                        continue
                    topic = str(x.get("study_topic", "")).strip()
                    if not topic:
                        topic = q[:60] + ("..." if len(q) > 60 else "")
                    expl = self._explanation_or_default(x.get("explanation"))

                    qt = str(x.get("question_type", "")).strip().lower()
                    if qt == "yes_no":
                        yn = self._parse_yes_no_answer(x.get("correct_answer"))
                        if yn is None:
                            continue
                        out.append({
                            "question_type": "yes_no",
                            "question": q,
                            "correct_answer": yn,
                            "study_topic": topic,
                            "explanation": expl,
                        })
                    elif qt in ("multiple_choice", "scenario", "code_mcq"):
                        opts = self._normalize_mc_options(x.get("options"))
                        if opts is None:
                            continue
                        letter = self._normalize_mc_letter(x.get("correct_answer"), opts)
                        if letter is None:
                            continue
                        out.append({
                            "question_type": qt,
                            "question": q,
                            "options": opts,
                            "correct_answer": letter,
                            "study_topic": topic,
                            "explanation": expl,
                        })
                if len(out) < PLAN_QUESTION_COUNT:
                    logger.warning(
                        "Parsed only %d/%d plan questions (dropped invalid rows or truncated JSON).",
                        len(out),
                        PLAN_QUESTION_COUNT,
                    )
                if out:
                    return out
            except (json.JSONDecodeError, ValueError):
                pass
        return [{
            "question_type": "yes_no",
            "question": "Skill fundamentals",
            "correct_answer": "Yes",
            "study_topic": "Skill fundamentals",
            "explanation": "Placeholder — model output was not valid JSON; retry the request.",
        }]

    async def generate_interview_readiness_plan(self, request: InterviewReadinessPlanRequest) -> list[dict]:
        """Holistic interview readiness: REAL_INTERVIEW_GENERATOR prompt + full request JSON; same JSON output contract."""
        full_user_json = json.dumps(
            request.model_dump(mode="json"),
            ensure_ascii=False,
            indent=2,
        )
        prompt = render_interview_readiness_prompt(
            full_user_json=full_user_json,
            plan_question_count=PLAN_QUESTION_COUNT,
        )

        async def call_openai():
            response = await self._client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=MAX_TOKENS_INTERVIEW_READINESS_PLAN,
            )
            content = response.choices[0].message.content or ""
            usage = getattr(response, "usage", None)
            if usage:
                tokens = getattr(usage, "total_tokens", 0) or 0
                logger.info("LLM tokens used: %d (interview readiness plan)", tokens)
            return self._parse_skill_readiness_plan(content)

        return await self.guard_layer.run_with_timeout(
            self.guard_layer.retry_with_fallback(call_openai)
        )

    async def generate_aptitude_readiness_plan(self, request) -> list[dict]:
        """Aptitude readiness: placement-oriented quant/logical/verbal medium-level quiz."""
        prompt = render_aptitude_readiness_prompt(
            user_type=request.user_type,
            experience_years=request.experience_years,
            primary_skill=request.primary_skill,
            target_role=request.target_role or "Software Engineer",
            target_company_type=request.target_company_type,
        )

        async def call_openai():
            response = await self._client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=MAX_TOKENS_SKILL_READINESS_PLAN,
            )
            content = response.choices[0].message.content or ""
            usage = getattr(response, "usage", None)
            if usage:
                tokens = getattr(usage, "total_tokens", 0) or 0
                logger.info("LLM tokens used: %d (aptitude readiness plan)", tokens)
            return self._parse_skill_readiness_plan(content)

        return await self.guard_layer.run_with_timeout(
            self.guard_layer.retry_with_fallback(call_openai)
        )

    def _parse_yes_no_answer(self, raw) -> str | None:
        s = str(raw).strip().lower()
        if s in ("yes", "y"):
            return "Yes"
        if s in ("no", "n"):
            return "No"
        return None

    def _normalize_mc_options(self, raw_opts) -> Optional[List[str]]:
        if not isinstance(raw_opts, list):
            return None
        opts: List[str] = []
        for o in raw_opts:
            if len(opts) >= 4:
                break
            t = str(o).strip() if o is not None else ""
            if t:
                opts.append(t[:400])
        if len(opts) != 4:
            return None
        return opts

    def _normalize_mc_letter(self, raw, options: List[str]) -> Optional[str]:
        s = str(raw).strip()
        if not s:
            return None
        u = s.upper()
        if len(u) == 1 and u in "ABCD":
            return u
        # "B)", "B.", "Answer: C", "option A"
        m = re.match(r"^[\s\(]*([ABCD])[\s\)\.:]", u)
        if m:
            return m.group(1)
        m2 = re.search(r"\b([ABCD])\b", u)
        if m2:
            return m2.group(1)
        for i, opt in enumerate(options):
            if opt.strip().lower() == s.lower():
                return chr(ord("A") + i)
        return None

    def _parse_legacy_plan(self, content: str) -> list[dict]:
        """Parse LLM JSON into LegacyPlanQuestionItem dicts (question, correct_answer, study_topic only)."""
        content = content.strip()
        json_match = re.search(r"\[[\s\S]*\]", content)
        if json_match:
            try:
                items = json.loads(json_match.group())
                if not isinstance(items, list):
                    raise ValueError("not a list")
                out: List[dict] = []
                for x in items[:PLAN_QUESTION_COUNT]:
                    if isinstance(x, dict) and "question" in x and "correct_answer" in x:
                        q = str(x["question"]).strip()
                        raw = str(x["correct_answer"]).strip().lower()
                        if raw == "yes":
                            a = "Yes"
                        elif raw == "no":
                            a = "No"
                        else:
                            continue
                        topic = str(x.get("study_topic", "")).strip()
                        if not topic:
                            topic = q[:60] + ("..." if len(q) > 60 else "")
                        if q:
                            out.append({"question": q, "correct_answer": a, "study_topic": topic})
                    elif isinstance(x, str) and x.strip():
                        q = x.strip()
                        out.append({
                            "question": q,
                            "correct_answer": "Yes",
                            "study_topic": q[:60] + ("..." if len(q) > 60 else ""),
                        })
                if out:
                    return out
            except (json.JSONDecodeError, ValueError):
                pass
        return [{
            "question": "Interview fundamentals",
            "correct_answer": "Yes",
            "study_topic": "Interview fundamentals",
        }]

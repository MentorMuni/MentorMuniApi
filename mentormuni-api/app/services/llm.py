from __future__ import annotations

import json
import logging
import re
from typing import List, Optional, Tuple
from difflib import SequenceMatcher
from openai import AsyncOpenAI
from app.core.config import settings as app_settings
from app.services.guard_layer import GuardLayer
from app.services.skill_readiness_prompt import render_skill_readiness_prompt
from app.services.interview_readiness_prompt import render_interview_readiness_prompt
from app.services.aptitude_readiness_prompt import render_aptitude_readiness_prompt
from app.services.ai_readiness_prompt import render_ai_readiness_prompt
from app.schemas.ai import InterviewReadinessPlanRequest

logger = logging.getLogger("llm_service")

MAX_TOKENS_LEGACY_PLAN = 1500
MAX_TOKENS_MIXED_PLAN = 3200
# TIER 2+++ MAXIMUM RELIABILITY: Set to 4000 tokens
# Model: gpt-3.5-turbo (200+ tok/s - proven on Railway)
# Strategy: Maximum tokens to ensure ZERO truncation
# LLM used 2061 at max, 4000 is 2x buffer
# With gpt-3.5-turbo (200 tok/s): 4000 tokens = 20 seconds generation
# With overhead: ~22 seconds (guaranteed complete, high-quality output)
MAX_TOKENS_INTERVIEW_READINESS_PLAN = 4000   # SET TO: 4000 (maximum reliability)
MAX_TOKENS_SKILL_READINESS_PLAN = 4000    # SET TO: 4000 (maximum reliability)
MAX_TOKENS_APTITUDE_READINESS_PLAN = 4000   # SET TO: 4000 (maximum reliability)
MAX_TOKENS_AI_READINESS_PLAN = 4000      # SET TO: 4000 (consistency)
MAX_TOKENS_VALIDATE = 20
PLAN_QUESTION_COUNT = 15
APTITUDE_SECTION_ORDER: list[str] = (
    ["quantitative"] * 5 + ["logical"] * 5 + ["verbal"] * 5
)


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
                    model="gpt-3.5-turbo",
                    messages=[{"role": "user", "content": prompt}],
                    max_tokens=MAX_TOKENS_VALIDATE,
                    temperature=0,
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
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=MAX_TOKENS_LEGACY_PLAN,
                temperature=0,
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
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=MAX_TOKENS_SKILL_READINESS_PLAN,
                temperature=0,
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
                        })
                    elif qt in ("multiple_choice", "scenario", "code_mcq"):
                        opts = self._normalize_mc_options(x.get("options"))
                        # BUG FIX: Add validation to ensure options are distinct and relevant
                        if opts is None or not self._validate_mc_options(opts, q):
                            logger.debug("Skipping MCQ with invalid/duplicate options: %s", q[:60])
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
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=MAX_TOKENS_INTERVIEW_READINESS_PLAN,
                temperature=0,
            )
            choice = response.choices[0]
            content = choice.message.content or ""
            if getattr(choice, "finish_reason", None) == "length":
                logger.warning(
                    "Interview readiness plan: LLM hit max_tokens (finish_reason=length); JSON may be truncated — expect fewer than %d questions or invalid tail rows.",
                    PLAN_QUESTION_COUNT,
                )
            usage = getattr(response, "usage", None)
            if usage:
                tokens = getattr(usage, "total_tokens", 0) or 0
                logger.info("LLM tokens used: %d (interview readiness plan)", tokens)
            return self._parse_skill_readiness_plan(content)

        return await self.guard_layer.run_with_timeout(
            self.guard_layer.retry_with_fallback(call_openai)
        )

    async def generate_aptitude_readiness_plan(self, request) -> list[dict]:
        """Aptitude readiness: placement-oriented quant/logical/verbal medium-level MCQ quiz."""
        prompt = render_aptitude_readiness_prompt(
            user_type=request.user_type,
            experience_years=request.experience_years,
            primary_skill=request.primary_skill,
            target_role=request.target_role or "Software Engineer",
            target_company_type=request.target_company_type,
        )

        async def call_openai():
            response = await self._client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You output only a single valid JSON object (no markdown). "
                            "The user message describes the required JSON shape including a \"questions\" array. "
                            "CRITICAL: ALL 4 OPTIONS PER QUESTION MUST BE MEANINGFULLY DIFFERENT. "
                            "Do NOT create options that differ only by punctuation, grammar, or pronoun."
                        ),
                    },
                    {"role": "user", "content": prompt},
                ],
                max_tokens=MAX_TOKENS_APTITUDE_READINESS_PLAN,
                temperature=0,
                response_format={"type": "json_object"},
            )
            choice = response.choices[0]
            if getattr(choice, "finish_reason", None) == "length":
                logger.warning(
                    "Aptitude readiness: LLM hit max_tokens (finish_reason=length); output may be truncated."
                )
            content = choice.message.content or ""
            usage = getattr(response, "usage", None)
            if usage:
                tokens = getattr(usage, "total_tokens", 0) or 0
                logger.info("LLM tokens used: %d (aptitude readiness plan)", tokens)
            parsed = self._parse_aptitude_readiness_plan(content)
            if len(parsed) != PLAN_QUESTION_COUNT:
                raise ValueError(
                    f"Incomplete aptitude plan: parsed {len(parsed)}/{PLAN_QUESTION_COUNT} valid questions "
                    "(output may be truncated, invalid JSON, or rows failed validation — check logs)."
                )
            return parsed

        return await self.guard_layer.run_with_timeout(
            self.guard_layer.retry_with_fallback(call_openai)
        )

    async def generate_ai_readiness_plan(self, request) -> list[dict]:
        """AI readiness: scenario-heavy beginner/intermediate all-MCQ quiz."""
        prompt = render_ai_readiness_prompt(
            user_type=request.user_type,
            experience_years=request.experience_years,
            primary_skill=request.primary_skill,
            target_role=request.target_role or "Software Engineer",
            ai_tools_used=getattr(request, "ai_tools_used", None),
            workflow_context=getattr(request, "workflow_context", None),
            plan_question_count=PLAN_QUESTION_COUNT,
        )

        async def call_openai():
            response = await self._client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=MAX_TOKENS_AI_READINESS_PLAN,
                temperature=0,
            )
            choice = response.choices[0]
            content = choice.message.content or ""
            if getattr(choice, "finish_reason", None) == "length":
                logger.warning(
                    "AI readiness: LLM hit max_tokens (finish_reason=length); output may be truncated."
                )
            usage = getattr(response, "usage", None)
            if usage:
                tokens = getattr(usage, "total_tokens", 0) or 0
                logger.info("LLM tokens used: %d (ai readiness plan)", tokens)
            parsed = self._parse_ai_readiness_plan(content)
            if len(parsed) != PLAN_QUESTION_COUNT:
                logger.warning(
                    "AI readiness plan returned %d/%d valid rows.",
                    len(parsed),
                    PLAN_QUESTION_COUNT,
                )
            return parsed

        return await self.guard_layer.run_with_timeout(
            self.guard_layer.retry_with_fallback(call_openai)
        )

    @staticmethod
    def _coerce_questions_list(obj) -> Optional[list]:
        if isinstance(obj, list):
            return obj
        if isinstance(obj, dict):
            for key in ("questions", "evaluation_plan", "items"):
                v = obj.get(key)
                if isinstance(v, list):
                    return v
        return None

    @classmethod
    def _extract_aptitude_questions_from_llm(cls, content: str) -> Optional[list]:
        """Parse JSON object {\"questions\": [...]} or a raw array from model output."""
        content = (content or "").strip()
        if not content:
            return None
        stripped = re.sub(r"^```(?:json)?\s*", "", content, flags=re.IGNORECASE | re.MULTILINE)
        stripped = re.sub(r"\s*```\s*$", "", stripped, flags=re.MULTILINE).strip()
        for candidate in (stripped, content):
            try:
                obj = json.loads(candidate)
                lst = cls._coerce_questions_list(obj)
                if lst is not None:
                    return lst
            except json.JSONDecodeError:
                pass
        m = re.search(r"\{[\s\S]*\}", content)
        if m:
            try:
                obj = json.loads(m.group())
                lst = cls._coerce_questions_list(obj)
                if lst is not None:
                    return lst
            except json.JSONDecodeError:
                pass
        m = re.search(r"\[[\s\S]*\]", content)
        if not m:
            return None
        try:
            obj = json.loads(m.group())
            lst = cls._coerce_questions_list(obj)
            return lst if lst is not None else (obj if isinstance(obj, list) else None)
        except json.JSONDecodeError:
            return None

    def _parse_aptitude_readiness_plan(self, content: str) -> list[dict]:
        """Parse aptitude plan JSON into up to 15 multiple_choice questions with strict 5/5/5 sections."""
        items = self._extract_aptitude_questions_from_llm(content)
        if not items:
            logger.warning("Aptitude plan: no JSON questions list found in model output.")
            return []

        out: List[dict] = []
        try:
            for x in items:
                if len(out) >= PLAN_QUESTION_COUNT:
                    break
                if not isinstance(x, dict) or "question" not in x:
                    continue
                q = str(x["question"]).strip()
                if not q:
                    continue
                opts = self._normalize_mc_options(x.get("options"))
                if opts is None:
                    logger.debug("Skipping aptitude MCQ with invalid option format: %s", q[:60])
                    continue
                
                # TRY FIX: Attempt to auto-fix similar options before rejecting
                fixed_opts = self._fix_similar_options(q, opts)
                if fixed_opts is None:
                    logger.debug("Skipping aptitude MCQ with unfixable similar options: %s", q[:60])
                    continue
                
                letter = self._normalize_mc_letter(x.get("correct_answer"), fixed_opts)
                if letter is None:
                    logger.debug("Skipping aptitude MCQ with invalid correct_answer: %s", q[:60])
                    continue
                topic = str(x.get("study_topic", "")).strip()
                if not topic:
                    topic = q[:60] + ("..." if len(q) > 60 else "")
                expl = self._explanation_or_default(x.get("explanation"))
                section = APTITUDE_SECTION_ORDER[len(out)]
                diff_raw = str(x.get("difficulty", "")).strip().lower()
                if diff_raw in ("easy", "moderate", "tricky"):
                    difficulty = diff_raw
                elif diff_raw in ("slightly tricky", "hard", "difficult"):
                    difficulty = "tricky"
                else:
                    difficulty = "moderate"
                asked_in = str(x.get("asked_in", "")).strip() or "Common pattern"
                if len(asked_in) > 200:
                    asked_in = asked_in[:200]
                why_fail = str(x.get("why_students_fail", "")).strip() or (
                    "Misread options or rushed under time pressure."
                )
                if len(why_fail) > 500:
                    why_fail = why_fail[:500]
                out.append({
                    "question_type": "multiple_choice",
                    "section": section,
                    "question": q,
                    "options": fixed_opts,
                    "correct_answer": letter,
                    "study_topic": topic,
                    "difficulty": difficulty,
                    "asked_in": asked_in,
                    "why_students_fail": why_fail,
                })
        except (TypeError, ValueError) as e:
            logger.error("Error parsing aptitude questions: %s", e)
            return []

        if len(out) < PLAN_QUESTION_COUNT:
            logger.warning(
                "Parsed only %d/%d aptitude questions (dropped invalid rows or truncated JSON).",
                len(out),
                PLAN_QUESTION_COUNT,
            )
        return out

    def _parse_ai_readiness_plan(self, content: str) -> list[dict]:
        """Parse AI readiness JSON into up to 15 multiple_choice questions."""
        items = self._extract_aptitude_questions_from_llm(content)
        if not items:
            logger.warning("AI readiness plan: no JSON questions list found in model output.")
            return []

        out: List[dict] = []
        try:
            for x in items:
                if len(out) >= PLAN_QUESTION_COUNT:
                    break
                if not isinstance(x, dict) or "question" not in x:
                    continue
                q = str(x["question"]).strip()
                if not q:
                    continue
                opts = self._normalize_mc_options(x.get("options"))
                if opts is None:
                    logger.debug("Skipping AI MCQ with invalid option format: %s", q[:60])
                    continue
                
                # TRY FIX: Attempt to auto-fix similar options before rejecting
                fixed_opts = self._fix_similar_options(q, opts)
                if fixed_opts is None:
                    logger.debug("Skipping AI MCQ with unfixable similar options: %s", q[:60])
                    continue
                
                letter = self._normalize_mc_letter(x.get("correct_answer"), fixed_opts)
                if letter is None:
                    logger.debug("Skipping AI MCQ with invalid correct_answer: %s", q[:60])
                    continue
                topic = str(x.get("study_topic", "")).strip()
                if not topic:
                    topic = q[:60] + ("..." if len(q) > 60 else "")
                expl = self._explanation_or_default(x.get("explanation"))
                out.append({
                    "question_type": "multiple_choice",
                    "question": q,
                    "options": fixed_opts,
                    "correct_answer": letter,
                    "study_topic": topic,
                })
        except (TypeError, ValueError) as e:
            logger.error("Error parsing AI readiness questions: %s", e)
            return []

        return out

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
        if isinstance(raw, (int, float)) and not isinstance(raw, bool):
            i = int(raw)
            if 1 <= i <= 4:
                return chr(ord("A") + i - 1)
        s = str(raw).strip()
        if not s:
            return None
        if s.isdigit():
            i = int(s)
            if 1 <= i <= 4:
                return chr(ord("A") + i - 1)
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

    def _validate_mc_options(self, options: List[str], question: str = "") -> bool:
        """
        PRODUCTION APTITUDE VALIDATION: Validates MCQ options rigorously but pragmatically.
        
        This validator is designed specifically for placement aptitude tests where:
        - Options often have similar wording by design (e.g., sentence correction)
        - Legitimate variations exist (pronouns, articles, verb forms)
        - Validation should reject only actual duplicates and near-identical options
        
        Checks:
        1. Exactly 4 options
        2. No exact/near-exact duplicates (case-insensitive, normalized whitespace, ignoring letter prefix)
        3. Each option has minimum meaningful length (>= 3 characters after removing prefix)
        4. Strict similarity only for near-identical pairs (>98%)
        
        Returns True if valid, False otherwise.
        """
        if len(options) != 4:
            logger.debug("MCQ validation failed: expected 4 options, got %d", len(options))
            return False
        
        # Helper to strip letter prefix and normalize
        def normalize_option(opt: str) -> str:
            # Remove leading letter prefix: "A) text" → "text"
            cleaned = re.sub(r'^[a-zA-Z]\)\s*', '', opt).strip()
            # Normalize whitespace and lowercase
            return " ".join(cleaned.lower().split())
        
        # Normalize all options once
        normalized_options = [normalize_option(opt) for opt in options]
        
        # Check 1: No exact duplicates
        unique_set = set(normalized_options)
        if len(unique_set) < 4:
            logger.warning("MCQ validation failed: duplicate options found in: %s", question[:60] if question else "unknown")
            logger.debug("Options: %s", options)
            return False
        
        # Check 2: Each option has minimum meaningful length (3 chars minimum after removing prefix)
        for i, norm_opt in enumerate(normalized_options):
            if len(norm_opt) < 3:
                logger.warning(
                    "MCQ validation failed: option[%d] too short ('%s') in: %s",
                    i, options[i][:50], question[:60] if question else "unknown"
                )
                return False
        
        # Check 3: Validate character similarity ONLY for near-identical pairs
        # We're lenient here because aptitude questions legitimately have similar options
        # Only reject if options are >98% identical (only whitespace/single-char differences)
        try:
            for i in range(len(normalized_options)):
                for j in range(i + 1, len(normalized_options)):
                    similarity = SequenceMatcher(None, normalized_options[i], normalized_options[j]).ratio()
                    
                    # REJECT only if nearly identical (>98%)
                    # This catches: "option, was" vs "option was" OR "exact duplicate" vs "exact duplicate"
                    if similarity > 0.98:
                        logger.warning(
                            "MCQ validation failed: options nearly identical (%.0f%% match): '%s' vs '%s'",
                            similarity * 100, options[i][:50], options[j][:50]
                        )
                        return False
        except Exception as e:
            logger.warning("MCQ validation similarity check failed: %s", e)
            return False
        
        return True


    def _fix_similar_options(self, question: str, options: List[str]) -> Optional[List[str]]:
        """
        POST-PROCESSING: Attempt to fix similar options that would fail validation.
        
        For aptitude tests, we're lenient since similar options are legitimate.
        This only tries to fix options that are >98% similar (near-identical).
        
        Returns fixed options if fixable, None if unfixable (skip question).
        """
        if len(options) != 4:
            return None
        
        # First, try validation as-is
        if self._validate_mc_options(options, question):
            return options
        
        # Find which pair(s) are too similar (>98%)
        problematic_pairs = []
        try:
            for i in range(len(options)):
                for j in range(i + 1, len(options)):
                    opt_i = options[i].lower().strip()
                    opt_j = options[j].lower().strip()
                    similarity = SequenceMatcher(None, opt_i, opt_j).ratio()
                    
                    if similarity > 0.98:
                        problematic_pairs.append((i, j, similarity))
        except Exception:
            return None
        
        if not problematic_pairs:
            return options
        
        # Try to fix by removing punctuation from one option in each pair
        fixed_options = list(options)
        for idx_i, idx_j, sim in problematic_pairs:
            opt_i = fixed_options[idx_i]
            opt_j = fixed_options[idx_j]
            
            # Remove punctuation to differentiate
            opt_i_no_punct = re.sub(r'[,;:!?.]', '', opt_i).strip()
            opt_j_no_punct = re.sub(r'[,;:!?.]', '', opt_j).strip()
            
            if opt_i_no_punct.lower() == opt_j_no_punct.lower():
                # They're identical except for punctuation
                if len(opt_i_no_punct) > len(opt_j_no_punct):
                    fixed_options[idx_j] = opt_i_no_punct
                else:
                    fixed_options[idx_i] = opt_j_no_punct
                logger.info("Auto-fixed punctuation difference in question: %s", question[:60])
                continue
            
            # Could not fix this pair
            logger.debug("Could not auto-fix similar options pair (%.0f%% match)", sim * 100)
            return None
        
        # Validate the fixed options
        if self._validate_mc_options(fixed_options, question):
            logger.info("Auto-fixed options in question: %s", question[:60])
            return fixed_options
        
        return None

    def _parse_legacy_plan(self, content: str) -> list[dict]:
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

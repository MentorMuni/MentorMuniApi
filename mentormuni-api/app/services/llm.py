from __future__ import annotations

import json
import logging
import re
from typing import List, Optional, Tuple
from openai import AsyncOpenAI
from app.core.config import settings
from app.services.guard_layer import GuardLayer
from app.services.skill_readiness_prompt import render_skill_readiness_prompt
from app.services.interview_readiness_prompt import render_interview_readiness_prompt
from app.schemas.ai import InterviewReadinessPlanRequest

logger = logging.getLogger("llm_service")

# LLM timeout in seconds (for 10k users, avoid long-running requests)
LLM_TIMEOUT = 30
MAX_TOKENS_LEGACY_PLAN = 1500
MAX_TOKENS_MIXED_PLAN = 3200
MAX_TOKENS_INTERVIEW_READINESS_PLAN = 10000
MAX_TOKENS_SKILL_READINESS_PLAN = 8000
MAX_TOKENS_VALIDATE = 20
PLAN_QUESTION_COUNT = 15


class LLMService:
    def __init__(self):
        self._client = AsyncOpenAI(api_key=settings.openai_api_key)
        self.guard_layer = GuardLayer(timeout=LLM_TIMEOUT)

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
                for x in items[:PLAN_QUESTION_COUNT]:
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

    @staticmethod
    def _prompt_user_category_for_interview_prompt(r: InterviewReadinessPlanRequest) -> str:
        """Maps canonical user_type to prompt vocabulary (college_year_1 … working_professional)."""
        m = {
            "college_student_year_1": "college_year_1",
            "college_student_year_2": "college_year_2",
            "college_student_year_3": "college_year_3",
            "college_student_year_4": "college_year_4",
            "recent_graduate": "recent_graduate",
            "it_professional": "working_professional",
        }
        return m.get(r.user_type, "college_year_4")

    @staticmethod
    def _target_company_for_interview_prompt(r: InterviewReadinessPlanRequest) -> str:
        sm, pc = r.targets_service_mnc, r.targets_product_company
        if sm is True and pc is True:
            return "both"
        if sm is True and pc is not True:
            return "service_mnc"
        if pc is True and sm is not True:
            return "product_company"
        return "both"

    def _format_interview_readiness_profile(self, r: InterviewReadinessPlanRequest) -> str:
        """Structured profile_block for interview_readiness_prompt (MODE A / MODE B)."""
        uc = self._prompt_user_category_for_interview_prompt(r)
        exp = r.experience_years if r.experience_years is not None else 0
        tr = (r.target_role or "").strip() or f"{r.primary_skill} Developer"
        lines: List[str] = [
            f"- user_category: {uc}",
            f"- experience_years: {exp}",
            f"- primary_skill: {r.primary_skill}",
            f"- target_role: {tr}",
            f"- target_company: {self._target_company_for_interview_prompt(r)}",
            "",
            "ADDITIONAL CONTEXT (optional; use for tone and scenarios only — do not invent facts not listed):",
        ]
        extra: List[str] = []
        if r.college_name:
            extra.append(f"- college_name: {r.college_name}")
        if r.assessment_focus:
            extra.append(f"- assessment_focus: {r.assessment_focus}")
        if r.current_organization:
            extra.append(f"- current_organization: {r.current_organization}")
        if r.user_category == "3rd_year":
            extra.append(
                "- placement_bucket_note: 1st–3rd year (fundamentals-heavy; no placement-company detail expected)"
            )

        if r.user_category in ("4th_year", "recent_graduate"):
            extra.append("placement_context:")
            if r.campus_or_off_campus:
                extra.append(f"  - campus_or_off_campus: {r.campus_or_off_campus}")
            if r.targets_service_mnc is not None:
                extra.append(f"  - targets_service_mnc: {r.targets_service_mnc}")
            if r.targets_product_company is not None:
                extra.append(f"  - targets_product_company: {r.targets_product_company}")
            if r.target_companies_notes:
                extra.append(f"  - target_companies_notes: {r.target_companies_notes}")
            if r.specific_role_requested is not None:
                extra.append(f"  - specific_role_requested: {r.specific_role_requested}")
            if r.specific_role:
                extra.append(f"  - specific_role: {r.specific_role}")
            if not any(
                [
                    r.campus_or_off_campus,
                    r.targets_service_mnc is not None,
                    r.targets_product_company is not None,
                    r.target_companies_notes,
                    r.specific_role_requested is not None,
                    r.specific_role,
                ]
            ):
                extra.append(
                    "  - (no step-13 placement extras — assume generic campus + off-campus mix)"
                )

        if r.user_category == "working_professional" or r.user_type == "it_professional":
            extra.append("professional_context:")
            if r.core_skill:
                extra.append(f"  - core_skill: {r.core_skill}")
            if r.jd_provided is not None:
                extra.append(f"  - jd_provided: {r.jd_provided}")
            if r.job_description:
                jd = r.job_description[:4000]
                if len(r.job_description) > 4000:
                    jd += " …[truncated]"
                extra.append(f"  - job_description_excerpt: {jd}")
            if r.target_company_name:
                extra.append(f"  - target_company_name: {r.target_company_name}")
            if not any([r.core_skill, r.jd_provided, r.job_description, r.target_company_name]):
                extra.append(
                    "  - (no JD/pro extras — use experience_years and primary_skill only)"
                )

        if not extra:
            lines.append("- (none)")
        else:
            lines.extend(extra)

        return "\n".join(lines)

    async def generate_interview_readiness_plan(self, request: InterviewReadinessPlanRequest) -> list[dict]:
        """Holistic interview readiness: full simulation prompt; yes_no + MC + scenario + code_mcq + explanations."""
        profile_block = self._format_interview_readiness_profile(request)
        tr = (request.target_role or "").strip() or f"{request.primary_skill} Developer"
        prompt = render_interview_readiness_prompt(
            profile_block=profile_block,
            primary_skill=request.primary_skill,
            target_role=tr,
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
        opts = []
        for o in raw_opts[:4]:
            t = str(o).strip() if o is not None else ""
            if not t:
                return None
            opts.append(t[:400])
        if len(opts) != 4:
            return None
        return opts

    def _normalize_mc_letter(self, raw, options: List[str]) -> Optional[str]:
        s = str(raw).strip()
        if not s:
            return None
        u = s.upper()
        if len(s) == 1 and u in "ABCD":
            return u
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

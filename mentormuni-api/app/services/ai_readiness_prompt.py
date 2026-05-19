"""Prompt template for POST /interview-ready/ai-readiness/plan."""

from __future__ import annotations

AI_READINESS_PROMPT = r"""
You are a senior AI engineering interviewer.

OBJECTIVE: Generate AI readiness test (beginner-intermediate level) for engineering students and working professionals. Feel like real interview pressure. Focus on practical AI use in engineering work, not theory.

Candidate: user_type __USER_TYPE__, experience __EXPERIENCE_YEARS__ years, skill __PRIMARY_SKILL__, target __TARGET_ROLE__, AI tools __AI_TOOLS_USED__, workflow __WORKFLOW_CONTEXT__

OUTPUT RULES:
1. EXACTLY {PLAN_QUESTION_COUNT} questions
2. ALL "multiple_choice" type (no yes_no/scenario/code_mcq)
3. Exactly 4 options (A-D) per question, one correct answer
4. Concise, interview-like stems (max 2 lines, code snippets OK)
5. Require reasoning, not pure theory
6. At least 8 scenario-based (incident, PR review, production bug, deadline pressure, etc.)
7. Practical focus (not theory-heavy)
8. No markdown, no commentary

JSON OUTPUT ONLY (valid array):
[{
  "question_type": "multiple_choice",
  "question": "string",
  "options": ["A) ...", "B) ...", "C) ...", "D) ..."],
  "correct_answer": "A" | "B" | "C" | "D",
  "study_topic": "2-4 words",
  "explanation": "2-3 lines"
}]
"""


def render_ai_readiness_prompt(
    *,
    user_type: str,
    experience_years: int | None,
    primary_skill: str,
    target_role: str,
    ai_tools_used: str | None,
    workflow_context: str | None,
    plan_question_count: int = 15,
) -> str:
    t = AI_READINESS_PROMPT.replace("{PLAN_QUESTION_COUNT}", str(plan_question_count))
    t = t.replace("__USER_TYPE__", str(user_type))
    t = t.replace("__EXPERIENCE_YEARS__", str(experience_years if experience_years is not None else 0))
    t = t.replace("__PRIMARY_SKILL__", str(primary_skill))
    t = t.replace("__TARGET_ROLE__", str(target_role))
    t = t.replace("__AI_TOOLS_USED__", str(ai_tools_used or "not specified"))
    t = t.replace("__WORKFLOW_CONTEXT__", str(workflow_context or "not specified"))
    return t

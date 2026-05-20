"""Prompt template for POST /interview-ready/skill-readiness/plan.

Placeholders: __USER_TYPE__, __EXPERIENCE_YEARS__, __PRIMARY_SKILL__, __TARGET_ROLE__, __TARGET_COMPANY_TYPE__
"""

# noqa: E501 — long prompt string
ULTIMATE_SKILL_ENGINE_PROMPT = r"""
You are a senior technical interviewer generating a high-signal skill readiness test.

CANDIDATE: User Type __USER_TYPE__, __EXPERIENCE_YEARS__ years, Skill __PRIMARY_SKILL__, Target __TARGET_ROLE__ at __TARGET_COMPANY_TYPE__.

OBJECTIVE: Generate EXACTLY 15 questions testing REAL understanding (not memorization). Test should feel like real interview filtering, not a basic quiz.

QUESTION MIX (MANDATORY):
- 8 Conceptual MCQ: test understanding, include confusing options
- 4 Scenario MCQ: real-world situations, ask "what would you do?", test decision-making
- 3 Yes/No MCQ: test misconceptions, NOT obvious

DIFFICULTY ADAPTATION:
- Years 1-2: fundamentals, simple scenarios
- Year 3: fundamentals + applied scenarios, moderate reasoning
- Year 4: interview-level, real-world scenarios, decision-making
- Professional: architecture, trade-offs, edge cases, system thinking

DESIGN RULES:
- 15-20 seconds per question
- Require thinking/elimination, not guessing
- Avoid definitions, obvious answers, or repeats
- Difficulty: 30% moderate, 50% strong, 20% tricky

SKILL FOCUS:
- LANGUAGE: code behavior, output prediction, memory, concurrency, edge cases (NOT syntax trivia)
- FRAMEWORK: architecture, lifecycle, dependency injection, real-world usage patterns (NOT "how do you import X?")
- PLATFORM: deployment, configuration, scaling, workflows (NOT just "what is this tool?")

FOR REAL INTERVIEWS:
- Prefer "What would fail at scale?" over "What is X?"
- Prefer "Debug this production error" over "Define X"
- Prefer "Compare approach A vs B" over "Name 3 patterns"
- Include: Actual gotchas engineers face, not textbook theory
- TCS/Infosys level: Optimization, performance, practical patterns
- Accenture/Product Co level: Architecture tradeoffs, edge cases, decision-making under constraints

OUTPUT FORMAT (VALID JSON ONLY):
[{
  "question_type": "multiple_choice" | "yes_no",
  "question": "clear and concise question",
  "options": ["A) ...", "B) ...", "C) ...", "D) ..."],
  "correct_answer": "A" | "B" | "C" | "D" | "Yes" | "No",
  "study_topic": "2-4 words",
  "difficulty": "moderate" | "strong" | "tricky",
  "explanation": "brief explanation"
}]

VALIDATION: Exactly 15 questions, correct distribution (8 MCQ, 4 scenario, 3 yes/no), no repeats, valid JSON only.
"""


def render_skill_readiness_prompt(
    user_type: str,
    experience_years: int,
    primary_skill: str,
    target_role: str,
    target_company_type: str,
) -> str:
    return ULTIMATE_SKILL_ENGINE_PROMPT.replace("__USER_TYPE__", user_type).replace(
        "__EXPERIENCE_YEARS__", str(experience_years)
    ).replace("__PRIMARY_SKILL__", primary_skill).replace("__TARGET_ROLE__", target_role).replace(
        "__TARGET_COMPANY_TYPE__", target_company_type
    )


# Backward-compatible name for imports
SKILL_READINESS_PLAN_PROMPT = ULTIMATE_SKILL_ENGINE_PROMPT

"""Prompt template for POST /interview-ready/skill-readiness/plan.

Placeholders: __USER_TYPE__, __EXPERIENCE_YEARS__, __PRIMARY_SKILL__, __TARGET_ROLE__, __TARGET_COMPANY_TYPE__
"""

# noqa: E501 — long prompt string
ULTIMATE_SKILL_ENGINE_PROMPT = r"""
You are a senior technical interviewer generating a skill readiness test.

CANDIDATE: __USER_TYPE__, __EXPERIENCE_YEARS__ years exp, __PRIMARY_SKILL__, targeting __TARGET_ROLE__ at __TARGET_COMPANY_TYPE__.

CRITICAL: Generate EXACTLY 15 questions. Mix of 4 types:
- 5 multiple_choice: conceptual understanding (NOT definitions)
- 3 scenario: real-world situations, decision-making
- 3 code_mcq: output prediction, bug finding (actual code)
- 4 yes_no: misconceptions, edge cases

DIFFICULTY BY EXPERIENCE:
- 0-2 years: 40% easy, 40% moderate, 20% tricky
- 3+ years: 20% easy, 40% moderate, 40% tricky
- Professionals: 10% easy, 40% moderate, 50% tricky

QUALITY RULES (CRITICAL - affects ALL questions):
✓ MUST test understanding, NOT memorization
✓ Each option must be PLAUSIBLE (make candidates think)
✓ Avoid obvious answers or trick questions
✓ Include real-world gotchas, not textbook theory
✓ NO repeats, NO duplicate concepts

QUESTION GUIDELINES:

multiple_choice (5 questions):
- Test architecture, patterns, design decisions
- Example: "Which approach best handles X scenario?"
- Include 2 reasonable options, 2 distractors
- Focus: "Why?" not "What is?"

scenario (3 questions):
- Real production situations: bugs, performance, scaling
- Format: "You see X problem in production. What do you check first?"
- Test problem-solving, not recall
- Include multiple reasonable approaches in options

code_mcq (3 questions):
- Actual code snippets (2-5 lines max)
- Ask: "What will this output?" OR "Find the bug"
- Test practical knowledge: scope, mutations, async, edge cases
- Include plausible wrong outputs

yes_no (4 questions):
- Test misconceptions: "Is X always true?" 
- Require reasoning (not obvious)
- Example: "Will this code always work in production?" Answer: No (explain why)

OUTPUT FORMAT (VALID JSON ARRAY ONLY):
[{
  "question_type": "multiple_choice",
  "question": "...",
  "options": ["Option A", "Option B", "Option C", "Option D"],
  "correct_answer": "A",
  "study_topic": "Topic",
  "explanation": "Why this is correct"
}, {
  "question_type": "yes_no",
  "question": "...",
  "correct_answer": "Yes",
  "study_topic": "Topic",
  "explanation": "Why Yes/No"
}, {
  "question_type": "scenario",
  "question": "...",
  "options": ["Approach A", "Approach B", "Approach C", "Approach D"],
  "correct_answer": "B",
  "study_topic": "Topic",
  "explanation": "Best approach"
}, {
  "question_type": "code_mcq",
  "question": "What does this output?\\nconst x = ...",
  "options": ["Output A", "Output B", "Output C", "Output D"],
  "correct_answer": "C",
  "study_topic": "Topic",
  "explanation": "Because..."
}]

VALIDATION CHECKLIST:
✓ Exactly 15 questions (5+3+3+4)
✓ All 4 types represented
✓ Valid JSON array (no markdown, no text)
✓ Each question has all required fields
✓ correct_answer is valid for that type (A-D for MCQ/scenario/code, Yes/No for binary)
✓ No repeating questions or concepts
✓ Explanations are concise and helpful

DO NOT output markdown, explanations, or text. ONLY output the JSON array.
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

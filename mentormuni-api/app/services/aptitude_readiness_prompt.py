"""Prompt template for POST /interview-ready/aptitude-readiness/plan.

CRITICAL: This prompt must be CONCISE to reduce token count while maintaining quality.
Placeholders: __USER_TYPE__, __EXPERIENCE_YEARS__, __PRIMARY_SKILL__, __TARGET_ROLE__, __TARGET_COMPANY_TYPE__
"""

# OPTIMIZED CONCISE PROMPT (500 tokens vs 2000 before)
APTITUDE_READINESS_PROMPT = r"""You are a placement aptitude test designer (TCS/Infosys/Wipro level).

TASK: Generate EXACTLY 15 multiple choice questions for campus placement.

STRUCTURE:
Q1-5: Quantitative (percentages, ratios, time & work, profit/loss, geometry)
Q6-10: Logical (syllogisms, coding, pattern recognition, puzzles)
Q11-15: Verbal (sentence correction, error spotting, comprehension)

OUTPUT FORMAT (ONLY JSON, NO MARKDOWN):
{
  "questions": [
    {
      "question_type": "multiple_choice",
      "section": "quantitative|logical|verbal",
      "question": "Clear question",
      "options": ["A) option1", "B) option2", "C) option3", "D) option4"],
      "correct_answer": "A|B|C|D",
      "study_topic": "Topic (2-5 words)",
      "difficulty": "easy|moderate|tricky",
      "asked_in": "TCS|Infosys|Wipro|Cognizant|Capgemini|Common",
      "why_students_fail": "One reason",
      "explanation": "Brief solution"
    },
    ... 14 more objects ...
  ]
}

CRITICAL RULES:
1. ALL OPTIONS MUST BE MEANINGFULLY DIFFERENT (not just punctuation/pronoun changes)
2. NEVER generate: "option, was" vs "option was" OR "She likes" vs "He likes"
3. Each option ≥3 chars
4. Difficulty mix: 70% moderate, 20% easy, 10% tricky
5. Return ONLY valid JSON (no markdown, no preamble)

CANDIDATE: __USER_TYPE__, __EXPERIENCE_YEARS__ yrs, __PRIMARY_SKILL__, Target: __TARGET_ROLE__, Company: __TARGET_COMPANY_TYPE__

VALIDATE BEFORE RETURNING:
✓ Exactly 15 questions
✓ Q1-5 quantitative, Q6-10 logical, Q11-15 verbal
✓ 4 distinct options per question
✓ Valid JSON only"""


def render_aptitude_readiness_prompt(
    user_type: str,
    experience_years: int,
    primary_skill: str,
    target_role: str,
    target_company_type: str,
) -> str:
    return APTITUDE_READINESS_PROMPT.replace("__USER_TYPE__", user_type).replace(
        "__EXPERIENCE_YEARS__", str(experience_years)
    ).replace("__PRIMARY_SKILL__", primary_skill).replace("__TARGET_ROLE__", target_role).replace(
        "__TARGET_COMPANY_TYPE__", target_company_type
    )

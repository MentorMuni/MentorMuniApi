"""Prompt template for POST /interview-ready/aptitude-readiness/plan.

Placeholders:
__USER_TYPE__, __EXPERIENCE_YEARS__, __PRIMARY_SKILL__, __TARGET_ROLE__, __TARGET_COMPANY_TYPE__
"""

# noqa: E501 — long prompt string
APTITUDE_READINESS_PROMPT = r"""You are a senior aptitude test designer for campus placements in India.

Your goal is to generate a high-quality aptitude readiness assessment for engineering students
preparing for placement interviews (TCS, Infosys, Wipro, Cognizant, Capgemini-style tests).

═══════════════════════════════════════
CANDIDATE PROFILE
═══════════════════════════════════════

- User Type      : __USER_TYPE__
- Experience     : __EXPERIENCE_YEARS__ years
- Skill Focus    : __PRIMARY_SKILL__
- Target Role    : __TARGET_ROLE__
- Target Company : __TARGET_COMPANY_TYPE__

Assume this is for engineering 4th year students targeting placement aptitude rounds.

═══════════════════════════════════════
OBJECTIVE
═══════════════════════════════════════

Generate EXACTLY 15 aptitude questions at MEDIUM difficulty.

Coverage must include all three areas:
1) Quantitative Aptitude
2) Logical Reasoning
3) Verbal Reasoning

Distribution target:
- 5 questions: Quantitative Aptitude
- 5 questions: Logical Reasoning
- 5 questions: Verbal Reasoning

Question style must resemble real IT-company placement aptitude tests used by TCS, Infosys, Wipro, Cognizant, Capgemini, Accenture and similar service MNCs.

Use common placement patterns:
- percentages, ratio-proportion, averages, profit-loss, time-work, time-speed-distance
- number/alphabet series, coding-decoding, blood relations, directions, syllogism
- reading comprehension, para-jumbles, sentence correction, vocabulary-in-context

═══════════════════════════════════════
MANDATORY JSON QUESTION TYPE — DO NOT DEVIATE
═══════════════════════════════════════

The response MUST be ONE JSON array of exactly 15 objects.

All 15 questions MUST be "multiple_choice" and follow this:
- Exactly 4 options labeled A) B) C) D)
- Exactly one correct option
- correct_answer: exactly "A", "B", "C", or "D"
- No yes_no, no scenario, no code_mcq types for aptitude-readiness.
- Keep stems concise and exam-like; avoid verbose interview framing.
- Use strict section order:
  - Questions 1-5: section = "quantitative"
  - Questions 6-10: section = "logical"
  - Questions 11-15: section = "verbal"

═══════════════════════════════════════
STRICT QUALITY RULES
═══════════════════════════════════════

1. Every question should be medium difficulty, not too easy and not olympiad-level.
2. Avoid purely definitional questions.
3. Keep language clear and concise.
4. All distractors must be plausible.
5. Each question must have a short and specific study_topic.
6. explanation is mandatory and must be 1-2 short sentences.
7. Ensure topics are varied and not repeated.
8. Keep calculations moderate; no very long or tricky arithmetic.
9. Avoid software coding questions; this is aptitude-only.

═══════════════════════════════════════
OUTPUT FORMAT — STRICT JSON ONLY
═══════════════════════════════════════

Return ONLY a raw JSON array of exactly 15 objects.
- No markdown fences
- No preamble or trailing text
- No extra keys

multiple_choice schema (for all 15 items):
{
  "question_type": "multiple_choice",
  "section": "quantitative" | "logical" | "verbal",
  "question": "string",
  "options": ["A) ...", "B) ...", "C) ...", "D) ..."],
  "correct_answer": "A" | "B" | "C" | "D",
  "study_topic": "string",
  "explanation": "string"
}
"""


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

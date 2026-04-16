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

Question style must resemble real placement aptitude tests used by service MNCs and similar companies.

═══════════════════════════════════════
MANDATORY JSON QUESTION TYPES — DO NOT DEVIATE
═══════════════════════════════════════

The response MUST be ONE JSON array of exactly 15 objects in this EXACT order:

Positions 1–4   → "yes_no"          (EXACTLY 4)
Positions 5–11  → "multiple_choice" (EXACTLY 7)
Positions 12–13 → "scenario"        (EXACTLY 2)
Positions 14–15 → "code_mcq"        (EXACTLY 2)

TYPE 1 — yes_no (positions 1–4)
- A precise claim related to aptitude logic/math/verbal correctness.
- correct_answer: exactly "Yes" or "No"
- At least 2 "Yes" and at least 1 "No"

TYPE 2 — multiple_choice (positions 5–11)
- Exactly 4 options labeled A) B) C) D)
- Exactly one correct option
- correct_answer: exactly "A", "B", "C", or "D"
- Use for arithmetic, percentages, ratios, time-work, syllogisms, sequences, grammar, vocabulary, sentence correction.

TYPE 3 — scenario (positions 12–13)
- Real placement-test style mini situation with four options and one best answer
- correct_answer: exactly "A", "B", "C", or "D"

TYPE 4 — code_mcq (positions 14–15)
- Use pseudo-logic snippets / pattern-based reasoning snippets in plain text with \n (NOT programming-framework trivia)
- Keep snippet 4–10 lines
- Ask output/logic correctness-style question
- correct_answer: exactly "A", "B", "C", or "D"

═══════════════════════════════════════
STRICT QUALITY RULES
═══════════════════════════════════════

1. Every question should be medium difficulty, not too easy and not olympiad-level.
2. Avoid purely definitional questions.
3. Keep language clear and concise.
4. All distractors must be plausible.
5. Each question must have a short and specific study_topic.
6. explanation is mandatory and must be 2-3 sentences.
7. Ensure topics are varied and not repeated.

═══════════════════════════════════════
OUTPUT FORMAT — STRICT JSON ONLY
═══════════════════════════════════════

Return ONLY a raw JSON array of exactly 15 objects.
- No markdown fences
- No preamble or trailing text
- No extra keys

yes_no schema:
{
  "question_type": "yes_no",
  "question": "string",
  "correct_answer": "Yes" | "No",
  "study_topic": "string",
  "explanation": "string"
}

multiple_choice / scenario / code_mcq schema:
{
  "question_type": "multiple_choice" | "scenario" | "code_mcq",
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

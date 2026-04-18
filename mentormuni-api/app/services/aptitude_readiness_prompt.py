"""Prompt template for POST /interview-ready/aptitude-readiness/plan.

Placeholders:
__USER_TYPE__, __EXPERIENCE_YEARS__, __PRIMARY_SKILL__, __TARGET_ROLE__, __TARGET_COMPANY_TYPE__
"""

# noqa: E501 — long prompt string
APTITUDE_READINESS_PROMPT = r"""
You are a senior aptitude test designer for campus placements in India.

Your task is NOT just to create questions,
but to evaluate a student's **real interview readiness under pressure**.

---

## 🎯 Objective:

Generate a high-quality aptitude readiness assessment for engineering students
preparing for placement tests of companies like TCS, Infosys, Wipro, Cognizant, Capgemini.

The test should:
- Reflect real placement test patterns (on-campus + off-campus)
- Be capable of eliminating weak candidates
- Reveal strengths and weaknesses
- Expose gaps in speed, accuracy, and thinking
- Feel like an actual screening test

---

## 📊 Test Structure:

Total Questions: 15
All MUST be "multiple_choice"

Strict order:
- Questions 1–5 → section = "quantitative"
- Questions 6–10 → section = "logical"
- Questions 11–15 → section = "verbal"

---

## 🏢 Real Placement Alignment:

Questions MUST reflect actual patterns asked in:
- TCS
- Infosys
- Wipro
- Cognizant
- Capgemini

Guidelines:
- Use commonly repeated patterns from previous placement tests
- Focus on realistic online assessment style questions
- Avoid overly academic or textbook-style problems

---

## ⚖️ Difficulty Distribution:

- 70% → moderate (core placement level)
- 20% → easy but time-sensitive (tests speed & accuracy)
- 10% → slightly tricky (tests thinking under pressure)

DO NOT create CAT-level or overly difficult questions.

---

## 🧠 Section Expectations:

### Quantitative:
- Percentages, ratios, averages, time & work, profit/loss
- Focus on calculation speed + clarity
- Include 1–2 slightly time-consuming problems

---

## 🚨 Logical Section (UPGRADED — CRITICAL):

DO NOT generate simple or obvious questions.

Include:
- Syllogisms
- Statement–conclusion / assumption
- Coding-decoding with twist
- Pattern recognition requiring 2–3 steps
- Small puzzles (not too long)

Questions should:
- require reasoning, not guessing
- not be solvable instantly
- force elimination of options

---

## 🚨 Verbal Section (UPGRADED — CRITICAL):

DO NOT generate basic synonym/antonym questions.

Include:
- Sentence correction (with very close options)
- Error spotting
- Para-jumbles
- Short comprehension-based questions

Options must:
- be similar and confusing
- require careful reading

---

## ⏱️ Performance Focus:

Design questions such that:
- A strong student can solve with focus and accuracy
- An average student struggles with elimination or time
- A weak student gets confused

The test must simulate **real pressure and decision-making**

---

## 🚫 Avoid:

- School-level or obvious questions
- Direct pattern recognition without thinking
- Pure theory or memory-based questions
- Repetitive formats

---

## 📦 Output Format (STRICT JSON — API CONTRACT):

Return ONLY one JSON object (no markdown fences, no text before or after). Root object MUST have exactly one key: "questions".

The "questions" value MUST be an array of exactly 15 objects, in order: positions 1–5 quantitative, 6–10 logical, 11–15 verbal (set "section" accordingly on each object).

Shape:
{
  "questions": [
    {
      "question_type": "multiple_choice",
      "section": "quantitative" | "logical" | "verbal",
      "question": "clear and concise question",
      "options": ["A) ...", "B) ...", "C) ...", "D) ..."],
      "correct_answer": "A" | "B" | "C" | "D",
      "study_topic": "short topic label",
      "difficulty": "easy" | "moderate" | "tricky",
      "asked_in": "TCS | Infosys | Wipro | Cognizant | Capgemini | Common pattern",
      "why_students_fail": "one short line",
      "explanation": "brief step-by-step (keep concise to save tokens)"
    }
  ]
}

Do not omit keys. Do not add extra top-level keys besides "questions".

---

## 🎯 Final Goal:

The test should feel like:
👉 "This can actually eliminate candidates in a real placement test"

It should help answer:
👉 "Am I actually ready to clear aptitude rounds?"

NOT:
👉 "Did I just solve easy practice questions?"

---

CANDIDATE CONTEXT (for tone only; do not ask biographical questions in stems):

- User Type: __USER_TYPE__
- Experience (years): __EXPERIENCE_YEARS__
- Skill focus: __PRIMARY_SKILL__
- Target role: __TARGET_ROLE__
- Target company type: __TARGET_COMPANY_TYPE__
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

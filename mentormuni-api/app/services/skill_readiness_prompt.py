"""Prompt template for POST /interview-ready/skill-readiness/plan.

Placeholders: __USER_TYPE__, __EXPERIENCE_YEARS__, __PRIMARY_SKILL__, __TARGET_ROLE__, __TARGET_COMPANY_TYPE__
"""


def render_skill_readiness_prompt(
    user_type: str,
    experience_years: int,
    primary_skill: str,
    target_role: str,
    target_company_type: str,
) -> str:
    return SKILL_READINESS_PLAN_PROMPT.replace("__USER_TYPE__", user_type).replace(
        "__EXPERIENCE_YEARS__", str(experience_years)
    ).replace("__PRIMARY_SKILL__", primary_skill).replace("__TARGET_ROLE__", target_role).replace(
        "__TARGET_COMPANY_TYPE__", target_company_type
    )


# noqa: E501 — long prompt string
SKILL_READINESS_PLAN_PROMPT = r"""You are a senior technical interviewer at a top-tier product company (think Google, Microsoft, or a funded startup).

Your task: Generate EXACTLY 15 interview questions that rigorously assess SKILL DEPTH and REASONING ABILITY
for the candidate's primary stack.

═══════════════════════════════════════
CANDIDATE PROFILE
═══════════════════════════════════════
- User Type      : __USER_TYPE__
  (Values: "college_student_year_1" | "college_student_year_2" | "college_student_year_3" |
           "college_student_year_4" | "it_professional")
- Experience     : __EXPERIENCE_YEARS__ years
  (For students: 0–1. For professionals: actual YOE.)
- Primary Skill  : __PRIMARY_SKILL__
- Target Role    : __TARGET_ROLE__
- Target Company : __TARGET_COMPANY_TYPE__
  (Values: "service_mnc" | "product_company" | "both")

═══════════════════════════════════════
SKILL BOUNDARY CONTRACT — READ FIRST, ENFORCE ALWAYS
═══════════════════════════════════════
EVERY single question in this quiz MUST stay within the strict boundary of __PRIMARY_SKILL__.

WHAT IS INSIDE THE BOUNDARY (allowed):
  • Core internals, mechanics, and runtime behavior of __PRIMARY_SKILL__
  • APIs, standard libraries, and built-in tools that are PART OF __PRIMARY_SKILL__
  • Syntax rules, language/framework-specific quirks and edge cases of __PRIMARY_SKILL__
  • Design patterns, idioms, and best practices SPECIFIC TO __PRIMARY_SKILL__
  • Performance, memory, and concurrency behavior AS IMPLEMENTED IN __PRIMARY_SKILL__
  • Common bugs, pitfalls, and misconceptions that are UNIQUE TO __PRIMARY_SKILL__
  • Version-specific behavior or deprecations within __PRIMARY_SKILL__

WHAT IS OUTSIDE THE BOUNDARY (forbidden):
  ✗ Any other programming language (even if "related" — e.g., if skill is Java, no Python/C++ questions)
  ✗ Any framework or library NOT shipped as part of __PRIMARY_SKILL__ itself
    (e.g., if skill is "Java", do NOT ask about Spring Boot unless __PRIMARY_SKILL__ = "Spring Boot")
  ✗ Generic CS theory not directly tied to how __PRIMARY_SKILL__ works
    (e.g., no abstract Big-O questions unless they test __PRIMARY_SKILL__'s specific complexity behavior)
  ✗ DevOps, CI/CD, cloud infrastructure, or tooling UNLESS __PRIMARY_SKILL__ IS that tool
  ✗ Database internals, SQL, or storage UNLESS __PRIMARY_SKILL__ IS a database skill
  ✗ System design UNLESS __PRIMARY_SKILL__ IS "System Design"
  ✗ HR, behavioral, or soft-skill questions — this is a pure technical quiz

BOUNDARY SELF-CHECK — apply to EVERY question before including it:
  Ask: "Could this question appear in a quiz for a DIFFERENT skill and still make sense?"
  → If YES → the question is too generic → rewrite or discard it
  Ask: "Does answering this question require specific knowledge of __PRIMARY_SKILL__?"
  → If NO  → the question is out of scope → rewrite or discard it

ALLOWED ADJACENCY (only if tightly coupled):
  You MAY reference adjacent concepts ONLY when they are inseparably part of __PRIMARY_SKILL__'s
  own specification or standard behavior.
  Example: Java → allowed to reference JVM memory model, garbage collection, java.util.*
  Example: React → allowed to reference Virtual DOM, JSX, React hooks — NOT Node.js or Webpack
  Example: SQL → allowed to reference indexes, transactions, query plans — NOT a specific DB engine
  If in doubt, stay inside the core skill. Never drift.

═══════════════════════════════════════
DIFFICULTY CALIBRATION — MANDATORY
═══════════════════════════════════════
Map experience to depth. Do NOT go above or below the candidate's level.

| experience_years | Depth Level  | What to cover                                                                  |
|------------------|--------------|--------------------------------------------------------------------------------|
| 0–1  (Yr 1)      | Beginner     | Syntax rules, data types, control flow, basic I/O, simple programs             |
| 1–2  (Yr 2)      | Foundational | OOP, standard libraries, common data structures, basic algorithms              |
| 2–3  (Yr 3)      | Intermediate | DSA, design patterns, debugging scenarios, optimization basics, mini projects  |
| 3–4  (Yr 4)      | Advanced     | System awareness, concurrency, APIs, real project scenarios, complexity        |
| 4–7  (Mid)       | Professional | Architecture tradeoffs, testing, performance, production debugging, CI/CD      |
| 7–12 (Senior)    | Senior       | System design, scalability, mentoring scenarios, advanced internals            |
| 12+  (Lead)      | Principal    | Org-wide tech decisions, cross-service design, tech strategy, innovation       |

═══════════════════════════════════════
MANDATORY QUESTION DISTRIBUTION — DO NOT DEVIATE
═══════════════════════════════════════
Total: EXACTLY 15 questions in this EXACT order and count:

Positions 1–4   → "yes_no"          (EXACTLY 4)
Positions 5–11  → "multiple_choice" (EXACTLY 7)
Positions 12–13 → "scenario"        (EXACTLY 2)
Positions 14–15 → "code_mcq"        (EXACTLY 2)

═══════════════════════════════════════
TYPE SPECIFICATIONS
═══════════════════════════════════════

TYPE 1 — yes_no (positions 1–4)
- Make a precise, non-obvious technical CLAIM about __PRIMARY_SKILL__ internals or behavior
- Candidate decides if the claim is true (Yes) or false (No)
- Target edge cases, common misconceptions, subtle behavior WITHIN __PRIMARY_SKILL__
- correct_answer MUST be exactly "Yes" or "No" (not "True"/"False")
- Distribute: at least 2 "Yes" and at least 1 "No" across the 4 questions
- FORBIDDEN: Do not start with "Is it true that..." — write the claim directly
- BOUNDARY CHECK: claim must be verifiable using ONLY __PRIMARY_SKILL__ knowledge

TYPE 2 — multiple_choice (positions 5–11)
- Test behavior, correctness, API contracts, performance tradeoffs IN __PRIMARY_SKILL__
- EXACTLY 4 options per question, labeled A) B) C) D)
- Exactly ONE correct answer; remaining 3 must be plausible distractors
- Distractors should represent real misconceptions developers hold ABOUT __PRIMARY_SKILL__
- correct_answer: exactly "A", "B", "C", or "D"
- BOUNDARY CHECK: all 4 options must reference only __PRIMARY_SKILL__ concepts

TYPE 3 — scenario (positions 12–13)
- Present a realistic work situation involving __PRIMARY_SKILL__ in production or development
- Candidate must pick the best technical action using __PRIMARY_SKILL__ knowledge
- Options A–D represent different __PRIMARY_SKILL__-specific approaches or diagnoses
- One option is clearly best within __PRIMARY_SKILL__; others are plausible but flawed
- correct_answer: exactly "A", "B", "C", or "D"
- BOUNDARY CHECK: the scenario resolution must require ONLY __PRIMARY_SKILL__ knowledge —
  do not introduce external tools, frameworks, or languages to solve it

TYPE 4 — code_mcq (positions 14–15)
- Show a SHORT code snippet (4–12 lines) written in __PRIMARY_SKILL__'s own syntax
- Ask ONE of: what does this output | what is the bug | what is printed | why does this fail
- Code must be syntactically valid UNLESS the question asks "what is wrong"
- Code must use ONLY __PRIMARY_SKILL__ built-in features — no third-party imports
- Use plain readable text for code — NO markdown backtick fences inside JSON strings
- Use \n for line breaks within the "question" string
- BOUNDARY CHECK: a developer who knows ONLY __PRIMARY_SKILL__ must be able to answer this
  without any outside knowledge

═══════════════════════════════════════
STRICT QUALITY RULES — ENFORCE ALL
═══════════════════════════════════════
1. NO definitional trivia — never ask "What is X?" or "What does X stand for?"
2. NO opinion questions — every question has a single defensible correct answer
3. NO repeated study_topic — all 15 must be distinct
4. ALL questions require active reasoning, not memorization
5. Distractors must be technically grounded — not comedy wrong answers
6. Difficulty spread within level: ~3 medium, ~7 hard, ~5 very hard (relative to level)
7. SKILL PURITY — every question must test __PRIMARY_SKILL__ ONLY — no cross-skill contamination
8. The "explanation" field is MANDATORY — 2–3 sentences explaining why the correct answer
   is right AND why the most tempting wrong answer is incorrect

═══════════════════════════════════════
OUTPUT FORMAT — STRICT JSON ONLY
═══════════════════════════════════════
Return ONLY a raw JSON array of exactly 15 objects.
- No markdown fences (no ```json)
- No preamble, commentary, or trailing text
- No keys other than those specified below
- Array must be parseable by JSON.parse() with zero pre-processing

yes_no schema:
{
  "question_type": "yes_no",
  "question": "string — the technical claim",
  "correct_answer": "Yes" | "No",
  "study_topic": "string — 3 to 6 words, specific to __PRIMARY_SKILL__",
  "explanation": "string — 2 to 3 sentences"
}

multiple_choice / scenario / code_mcq schema:
{
  "question_type": "multiple_choice" | "scenario" | "code_mcq",
  "question": "string",
  "options": ["A) ...", "B) ...", "C) ...", "D) ..."],
  "correct_answer": "A" | "B" | "C" | "D",
  "study_topic": "string — 3 to 6 words, specific to __PRIMARY_SKILL__",
  "explanation": "string — 2 to 3 sentences"
}

═══════════════════════════════════════
FINAL VALIDATION CHECKLIST
(run this check mentally before outputting — fix any failure before responding)
═══════════════════════════════════════
[ ] Exactly 15 objects in the array
[ ] Positions 1–4 are all "yes_no"
[ ] Positions 5–11 are all "multiple_choice"
[ ] Positions 12–13 are all "scenario"
[ ] Positions 14–15 are all "code_mcq"
[ ] Every object has: question_type, question, correct_answer, study_topic, explanation
[ ] Every multiple_choice / scenario / code_mcq has exactly 4 options
[ ] No two questions share a study_topic
[ ] Output is valid JSON — no trailing commas, no inline comments
[ ] SKILL BOUNDARY: every question passes both boundary self-checks:
      → "Could this question appear in a quiz for a different skill?" → NO
      → "Does answering require specific __PRIMARY_SKILL__ knowledge?"  → YES
[ ] No question references an external language, tool, or framework
    outside the core specification of __PRIMARY_SKILL__
"""

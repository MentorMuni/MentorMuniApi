"""Prompt template for POST /interview-ready/aptitude-readiness/plan.

Placeholders:
__USER_TYPE__, __EXPERIENCE_YEARS__, __PRIMARY_SKILL__, __TARGET_ROLE__, __TARGET_COMPANY_TYPE__
"""

# noqa: E501 — long prompt string
APTITUDE_READINESS_PROMPT = r"""
You are a senior aptitude test designer for campus placements at TCS, Infosys, Wipro, Cognizant, Capgemini.

OBJECTIVE: Generate EXACTLY 15 high-quality, realistic placement-test multiple choice questions that assess practical aptitude, not just theory.

TEST STRUCTURE (MANDATORY):
- Questions 1-5: Quantitative Reasoning (percentages, ratios, time & work, profit/loss, geometry)
- Questions 6-10: Logical Reasoning (syllogisms, assumptions, coding-decoding, pattern recognition, puzzles)
- Questions 11-15: Verbal & Reading (sentence correction, error spotting, comprehension, para-jumbles)

EACH QUESTION FORMAT (STRICT):
{
  "question_type": "multiple_choice",
  "section": "quantitative" | "logical" | "verbal",
  "question": "clear, single-sentence or compound question",
  "options": ["A) first unique option", "B) second unique option", "C) third unique option", "D) fourth unique option"],
  "correct_answer": "A" | "B" | "C" | "D",
  "study_topic": "short topic label (2-5 words, not the question itself)",
  "difficulty": "easy" | "moderate" | "tricky",
  "asked_in": "TCS | Infosys | Wipro | Cognizant | Capgemini | Common pattern",
  "why_students_fail": "one-sentence reason why students often miss this",
  "explanation": "brief step-by-step solution (2-3 sentences)"
}

CRITICAL OPTION QUALITY RULES (MUST FOLLOW):
=====================================================

1. ALL 4 OPTIONS MUST BE MEANINGFULLY DIFFERENT
   - REJECT options that differ only by: punctuation, grammar, single pronoun, or article
   - EACH option must represent a DISTINCT concept, value, or approach
   - Example of BAD options (NEVER DO THIS):
     ✗ A) "that I borrowed from the library, was"
     ✗ B) "that I borrowed from the library was"
     (These differ only by comma - WRONG)
     ✗ A) "She doesn't like ice cream"
     ✗ B) "He doesn't like ice cream"
     (These differ only by pronoun - WRONG)

2. EACH OPTION MINIMUM LENGTH: 3 characters
   - No single-letter or 2-character options like "3" or "A)"
   - Use full context: "3 days" instead of "3"

3. OPTIONS MUST BE SUBSTANTIVELY DIFFERENT:
   - Good Example (Verbal - Sentence Correction):
     A) "The committee are making a decision" (wrong: plural verb)
     B) "The committee is making a decision" (correct: singular)
     C) "The committee were made decisions" (wrong: grammar)
     D) "The committee make deciding" (wrong: grammar)
   - Good Example (Quantitative):
     A) 25% (wrong calculation)
     B) 50% (correct answer)
     C) 75% (wrong calculation)
     D) 100% (wrong calculation)

4. FOR SIMILAR SOUNDING OPTIONS (ALLOWED only if truly different):
   Good: "weak understanding" vs "limited comprehension" (different concepts)
   Good: "increased speed" vs "improved efficiency" (different metrics)
   Bad: "weak" vs "unclear" when they mean same thing in context
   Bad: "increased" vs "increasing" (only tense differs)

DIFFICULTY DISTRIBUTION (PER SECTION):
- 70% Moderate: Requires focus, not guessing, place discrimination level
- 20% Easy but tricky: Time-sensitive or common mistakes
- 10% Challenging: Tests deep understanding

COMPANY-SPECIFIC PATTERNS:
Service Companies (TCS/Infosys/Wipro):
- 40% optimization & efficiency problems
- 30% pattern & code-based reasoning
- 30% practical real-world scenarios

Consulting (Accenture/Capgemini):
- 35% business scenario thinking
- 30% system & process analysis
- 25% optimization
- 10% client communication

Product (Google/Microsoft):
- 40% algorithm & structure optimization
- 30% system design thinking
- 20% edge cases & boundary conditions
- 10% practical implementations

OUTPUT (MANDATORY):
==================
Return ONLY a valid JSON object in this EXACT format:
{
  "questions": [
    {question object 1},
    {question object 2},
    ... EXACTLY 15 question objects in order ...
  ]
}

VALIDATION CHECKLIST (BEFORE OUTPUTTING):
- [ ] Exactly 15 question objects in "questions" array
- [ ] Questions 1-5 have section="quantitative"
- [ ] Questions 6-10 have section="logical"
- [ ] Questions 11-15 have section="verbal"
- [ ] All 4 options per question are MEANINGFULLY DIFFERENT (not just punctuation/pronoun variations)
- [ ] Each option is at least 3 characters
- [ ] correct_answer is one of: A, B, C, D
- [ ] difficulty is one of: easy, moderate, tricky
- [ ] study_topic is 2-5 words (not the full question)
- [ ] All text is clear English (no gibberish)

CANDIDATE CONTEXT: __USER_TYPE__, __EXPERIENCE_YEARS__ years, __PRIMARY_SKILL__, Target: __TARGET_ROLE__, Company: __TARGET_COMPANY_TYPE__.

SUCCESS = Questions that realistically assess interview preparation, with high-quality distinct options that require thinking, not guessing.
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

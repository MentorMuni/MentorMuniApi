"""coding_analysis_v1 — teaching/coaching only; never decides pass/fail."""

PROMPT_VERSION = "coding_analysis_v1"

CODING_ANALYSIS_SYSTEM = """You are MentorMuni's coding coach for campus placement prep.
You NEVER execute code and NEVER invent whether tests passed — execution evidence is given.
Official grade is already computed from tests; you produce coaching scores and teaching only.
Respond with a single JSON object matching the schema. Be concrete and beginner-friendly.
"""


def render_coding_analysis_prompt(
    *,
    problem_title: str,
    problem_description: str,
    constraints: str,
    expected_complexity: str,
    expected_approach: str,
    language: str,
    source_code: str,
    passed: int,
    total: int,
    official_score: float,
    verdict: str,
    failed_categories: list[str],
    execution_metrics: str,
) -> str:
    return f"""Analyze this student submission for placement coding prep.

PROBLEM TITLE: {problem_title}

PROBLEM:
{problem_description}

CONSTRAINTS:
{constraints}

EXPECTED TIME/SPACE: {expected_complexity}
EXPECTED APPROACH: {expected_approach}

LANGUAGE: {language}

OFFICIAL EXECUTION EVIDENCE (authoritative — do not contradict):
- tests_passed: {passed}/{total}
- official_score: {official_score}
- verdict: {verdict}
- failed_categories: {failed_categories}
- metrics: {execution_metrics}

STUDENT SOURCE CODE:
```{language}
{source_code[:12000]}
```

Return JSON with this exact shape:
{{
  "overall_coaching_score": 0-100,
  "correctness": {{"score": 0-100, "summary": "..."}},
  "approach": {{"detected": "...", "score": 0-100, "quality": "..."}},
  "complexity": {{"time": "O(...)", "space": "O(...)", "score": 0-100}},
  "code_quality": {{"score": 0-100, "summary": "..."}},
  "edge_cases": {{"score": 0-100, "summary": "..."}},
  "constraint_awareness": {{
    "understood_constraints": true/false,
    "complexity_appropriate_for_constraints": true/false,
    "missed_scalable_approach": true/false,
    "notes": "..."
  }},
  "mistakes": [{{"type": "...", "severity": "low|medium|high", "explanation": "...", "beginner_explanation": "..."}}],
  "better_approach": {{"name": "...", "explanation": "...", "time_complexity": "...", "space_complexity": "..."}},
  "beginner_explanation": "...",
  "strengths": ["..."],
  "learning_gaps": ["..."],
  "next_learning_focus": ["..."]
}}

Constraint-awareness is mandatory: did they understand input limits, is complexity appropriate, did they miss a scalable approach?
Explain mistakes simply (mental models, not jargon dumps).
"""

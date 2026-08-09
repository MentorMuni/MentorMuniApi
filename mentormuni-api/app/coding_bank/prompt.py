"""Versioned OpenAI prompt for original placement-oriented coding problems."""

from __future__ import annotations

from typing import Any

from app.coding_bank import PROMPT_VERSION
from app.coding_bank.schemas import GENERATED_PROBLEM_JSON_SCHEMA

CODING_PROBLEM_GENERATION_SYSTEM = """You are MentorMuni's coding problem author for campus placement prep.
You create ORIGINAL algorithmic problems that test known patterns with fresh wording,
examples, and test data.

AUDIENCE DEFAULT:
- Final-year (4th year) engineering students appearing for campus placements
  (product + service companies: Microsoft, Amazon, Google, TCS, Infosys, etc.).
- Problems should feel like campus coding-round / OA practice — clear, fair, teachable.

HARD RULES:
- Do NOT imitate or reproduce proprietary wording from LeetCode, HackerRank, CodeSignal,
  company OA banks, or other copyrighted question banks.
- Do NOT copy famous problem titles verbatim when avoidable; invent an original framing.
- Do NOT claim a problem is an official interview question from any company.
- Company context (if provided) is ONLY for difficulty/theme alignment and relevance metadata,
  never for cloning a company's private assessment.
- Problem statement, constraints, examples, reference solution, and tests MUST be
  internally consistent.
- Reject ambiguity: every requirement must be explicit.
- Never invent contradictory constraints or impossible examples.
- Never leave unexplained assumptions about input/output formats.
- Reference solutions must be correct for the stated problem.
- Candidate test inputs must be valid under the constraints.
- Prefer stdin/stdout competitive-programming style I/O that matches starter code.
- Respond with a single JSON object matching the provided schema. No markdown fences.
"""


def render_generation_user_prompt(
    *,
    difficulty: str,
    topic: str,
    pattern: str,
    expected_time_complexity: str,
    expected_space_complexity: str,
    avoid_titles: list[str] | None = None,
    avoid_slugs: list[str] | None = None,
    extra_notes: str | None = None,
    company_name: str | None = None,
) -> str:
    avoid_titles = avoid_titles or []
    avoid_slugs = avoid_slugs or []
    avoid_block = ""
    if avoid_titles or avoid_slugs:
        avoid_block = (
            "\nAVOID near-duplicates of these existing bank items "
            f"(titles={avoid_titles[:30]!r}, slugs={avoid_slugs[:30]!r}).\n"
        )
    notes = f"\nADDITIONAL NOTES:\n{extra_notes}\n" if extra_notes else ""
    company_block = ""
    if company_name:
        company_block = (
            f"\nCOMPANY THEME (optional alignment only): {company_name}\n"
            "Align difficulty/style with typical campus coding rounds for this company type.\n"
            "Do NOT reproduce any proprietary company question. Do NOT claim official authorship.\n"
        )
    return f"""Generate ONE original placement-oriented coding problem.

TARGET AUDIENCE: 4th-year engineering students preparing for campus software placements.

TARGETS:
- difficulty: {difficulty}
- topic: {topic}
- pattern: {pattern}
- expected_time_complexity: {expected_time_complexity}
- expected_space_complexity: {expected_space_complexity}
{company_block}{avoid_block}{notes}
REQUIREMENTS:
1. Original wording, examples, and test data (pattern may be classic; wording must not be).
2. Clear input format and output format (stdin/stdout).
3. Constraints that match difficulty and expected complexity.
4. At least 2 worked examples with explanations.
5. Starter code for python, cpp, and java (function/IO stubs only).
6. At least one correct python reference solution that reads stdin and writes stdout.
7. At least 8 candidate test cases spanning categories:
   normal, boundary, minimum, maximum, and applicable of:
   duplicates, empty, single, negative, adversarial, large.
8. Set is_hidden=true for harder/edge cases; keep a few public (is_hidden=false).
9. You MAY fill expected_output tentatively; validators will recompute from the reference.
10. Include explanation of the intended approach.

PROHIBITED:
- Ambiguous requirements
- Contradictory constraints
- Impossible examples
- Duplicate bank problems
- Unexplained assumptions
- Incorrect reference solutions
- Test cases that contradict the statement

Return JSON only.
PROMPT_VERSION={PROMPT_VERSION}
"""


def openai_response_format() -> dict[str, Any]:
    """Strict JSON schema wrapper for OpenAI structured outputs."""
    return {
        "type": "json_schema",
        "json_schema": {
            "name": "generated_coding_problem",
            "strict": True,
            "schema": _openai_strict_schema(GENERATED_PROBLEM_JSON_SCHEMA),
        },
    }


def _openai_strict_schema(schema: dict[str, Any]) -> dict[str, Any]:
    """Best-effort conversion toward OpenAI strict JSON schema constraints."""
    out = dict(schema)
    # OpenAI strict mode wants additionalProperties:false on objects.
    if out.get("type") == "object" or "properties" in out:
        out["additionalProperties"] = False
        props = out.get("properties") or {}
        out["required"] = list(props.keys())
        out["properties"] = {k: _openai_strict_schema(v) if isinstance(v, dict) else v for k, v in props.items()}
    if "$defs" in out:
        out["$defs"] = {
            k: _openai_strict_schema(v) if isinstance(v, dict) else v for k, v in out["$defs"].items()
        }
    if "definitions" in out:
        out["definitions"] = {
            k: _openai_strict_schema(v) if isinstance(v, dict) else v for k, v in out["definitions"].items()
        }
    if "items" in out and isinstance(out["items"], dict):
        out["items"] = _openai_strict_schema(out["items"])
    if "anyOf" in out:
        out["anyOf"] = [_openai_strict_schema(x) if isinstance(x, dict) else x for x in out["anyOf"]]
    return out

"""Prompt for post-interview voice session analysis (structured scoring).

Placeholders: **INTERVIEW_FOCUS**, **TARGET_COMPANIES**, **TARGET_ROLE**, **TRANSCRIPT**
"""

from typing import Optional

VOICE_INTERVIEW_ANALYSIS_PROMPT = r"""You are a senior technical interview evaluator for Indian IT MNC campus hiring
(TCS, Infosys, Wipro, Persistent, Nagarro and similar).

Analyze the LIVE PRACTICE INTERVIEW transcript below for a final-year engineering student.

INTERVIEW FOCUS: **INTERVIEW_FOCUS**
TARGET ROLE: **TARGET_ROLE**
TARGET COMPANIES: **TARGET_COMPANIES**

TRANSCRIPT (speaker turns):
---
**TRANSCRIPT**
---

SCORING RULES
- technical_score (0–100): correctness, depth, and relevance of answers to INTERVIEW_FOCUS.
- communication_score (0–100): clarity, structure, confidence, spoken English for MNC interviews.
- Be realistic for campus / early-career bars — not FAANG-only harshness, not inflated praise.
- If the transcript is very short or empty, score conservatively (typically 35–55) and explain gaps in weaknesses/study_plan.

OUTPUT (STRICT JSON ONLY — no markdown, no commentary)
{
  "technical_score": <integer 0-100>,
  "communication_score": <integer 0-100>,
  "strengths": ["...", "..."],
  "weaknesses": ["...", "..."],
  "study_plan": ["...", "..."]
}

CONSTRAINTS
- strengths: 2–5 short concrete items tied to what the candidate actually said.
- weaknesses: 2–5 short concrete improvement areas.
- study_plan: 3–6 actionable next steps for MNC interview prep related to INTERVIEW_FOCUS.
- Do not invent skills the candidate never demonstrated.
- Prefer specific topics (e.g. "Java Collections — HashMap vs ConcurrentHashMap") over vague praise.
"""


def render_voice_interview_analysis_prompt(
    interview_focus: str,
    transcript: str,
    *,
    target_role: Optional[str] = None,
    target_companies: Optional[str] = None,
) -> str:
    focus = (interview_focus or "").strip() or "general technical interview"
    text = (transcript or "").strip() or "(No transcript captured.)"
    return (
        VOICE_INTERVIEW_ANALYSIS_PROMPT.replace("**INTERVIEW_FOCUS**", focus)
        .replace("**TARGET_ROLE**", (target_role or "Software Engineer / Graduate Trainee").strip())
        .replace(
            "**TARGET_COMPANIES**",
            (target_companies or "TCS, Infosys, Wipro, Persistent, Nagarro").strip(),
        )
        .replace("**TRANSCRIPT**", text)
    )

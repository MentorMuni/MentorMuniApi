"""Prompts for Aptitude Arcade OpenAI generation."""

from __future__ import annotations

ARCADE_SYSTEM = """You are an expert Indian campus placement aptitude coach.
Generate fresh exam-style aptitude questions as strict JSON only.
Rules:
- Questions must be solvable with unique correct answers.
- Difficulty mix: ~40% easy, ~40% medium, ~20% hard.
- No duplicate questions in the batch.
- Keep language clear for engineering students (TCS/Infosys/Wipro style).
- Do not include markdown fences or commentary outside JSON.
"""


def build_arcade_user_prompt(*, game_id: str, count: int) -> str:
    schemas = {
        "seating_shuffle": f"""
game_id: seating_shuffle
Return JSON: {{"questions":[ ... exactly {count} items ... ]}}
Each item:
{{
  "clues": ["string", "..."],          // 3-6 short clues
  "seats": 4|5|6,                      // number of seats
  "solution": ["A","B",...],           // left→right order, length == seats, unique letters
  "facing": "Linear row, left → right.",
  "solutionText": "A – B – C …"
}}
Use letters only (A–F). solution must match clues exactly.
""",
        "family_tree_rush": f"""
game_id: family_tree_rush
Return JSON: {{"questions":[ ... exactly {count} items ... ]}}
Each item:
{{
  "q": "Blood relation question text?",
  "options": ["Opt1","Opt2","Opt3","Opt4"],  // exactly 4
  "answer": "Opt1",                           // must equal one option
  "solution": "One-line reasoning.",
  "tip": "Short tip."
}}
Classic placement blood-relation style.
""",
        "rail_rush": f"""
game_id: rail_rush
Return JSON: {{"questions":[ ... exactly {count} items ... ]}}
Each item:
{{
  "label": "Opposite direction — meet" | "Same direction — chase",
  "length": number,          // distance/gap in km (>0)
  "speedA": number,          // km/h (>0)
  "speedB": number,          // km/h (>0); for chase speedA > speedB
  "opposite": true|false,    // true=meet, false=chase
  "question": "Question asking for time in hours?",
  "answer": number,          // exact hours = length/(speedA+speedB) OR length/(speedA-speedB)
  "formula": "expression",
  "solution": "Short solution sentence."
}}
Ensure answer matches the formula mathematically.
""",
        "factory_floor": f"""
game_id: factory_floor
Return JSON: {{"questions":[ ... exactly {count} items ... ]}}
Each item:
{{
  "title": "Job pack N",
  "workers": int,      // current workers (>=2)
  "days": int,         // days they take (>=2)
  "targetDays": int,   // desired days, strictly less than days
  "tip": "Man-days = workers × days.",
  "solution": "Explain needed workers = ceil((workers*days)/targetDays)."
}}
targetDays must be < days. Numbers should be clean integers.
""",
        "pattern_pulse": f"""
game_id: pattern_pulse
Return JSON: {{"questions":[ ... exactly {count} items ... ]}}
Each item:
{{
  "nums": [n1,n2,n3,n4,"?"],   // 4 numbers then "?"
  "answer": number,            // missing term
  "rule": "Brief rule (AP / squares / multiples…)",
  "solution": "Short calculation."
}}
Use clear AP, multiples, squares, cubes, or +n² patterns.
""",
    }
    body = schemas.get(game_id)
    if not body:
        raise ValueError(f"Unknown game_id: {game_id}")
    return (
        f"Generate a fresh pack of {count} unique questions for MentorMuni Aptitude Arcade.\n"
        f"{body}\n"
        "Return only the JSON object."
    )

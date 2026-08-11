"""Morning mentorship prompt — ground-level mentor, not a motivational poster."""

from __future__ import annotations

from typing import Any

WHITEBOARD_MENTOR_SYSTEM = """
You are a campus placement mentor who sits with the student, not above them.
You have 12 years placing engineering students into product and service companies in India.
You do not give hope. You give the exact next move that closes the note if they follow it.

VOICE:
- Direct. Warm. Slightly older-cousin, not HR, not LinkedIn guru.
- Indian campus English is fine. No corporate sludge. No "believe in yourself".
- Never diagnose mental health. Never say anxiety/depression. Say stuck, frozen, overloaded.
- Never invent facts they did not write. If a note is vague, the action is how to make it concrete today.

WHAT YOU SEE:
- YESTERDAY'S NOTES: the only new problems you are solving today. These are the main job.
- STILL OPEN FROM BEFORE: leftover notes they did not peel. Call them out. Do not pretend they vanished.
- PEELED / SOLVED: they removed the note, so that issue is done. Congratulate in one line, then do not re-coach it.
- PREVIOUS MORNING DROP: so you do not repeat yesterday's plan unless they ignored it.

YOUR JOB:
For each open yesterday-note (and lingering open notes if yesterday was thin), write an action so specific that:
- a confused 3rd-year can start in the next 10 minutes
- if they do it exactly, that sticky note can be peeled tonight
- there is a clear "done when" test, not a vibe

OUTPUT MUST BE STRICT JSON:
{
  "headline": "One sharp line that names today's real problem. Not generic.",
  "greeting": "One sentence. Use their first name. You read the board.",
  "what_changed": "What got peeled vs what is still stuck. Name the notes in their words.",
  "diagnosis": "2-4 sentences. The actual mechanism of the problem, not the feeling. Example: you are watching solutions instead of failing on paper for 20 minutes.",
  "actions": [
    {
      "order": 1,
      "title": "Short verb phrase",
      "do_exactly": "Step-by-step. Named resource, timer, what to type/write/say. No fluff.",
      "why_this_works": "One sentence tying it to THEIR note.",
      "done_when": "Observable finish line. If they can screenshot it, it is done.",
      "timebox_minutes": 25,
      "note_ids": [12]
    }
  ],
  "callout": "If they only do one thing today, this is it — and why that note dies tonight.",
  "closing": "Short. No TED talk. Push them to peel the note only when the done-when is true."
}

RULES:
- 2 to 4 actions. Never more than 4. Rank by what unblocks placement fastest.
- Every action maps to at least one note_id from the lists you were given. Do not invent ids.
- If a note is already peeled, do not create an action for it.
- If yesterday had no new notes but older notes are still open, coach those open notes. Say you noticed they added nothing new.
- Prefer today's calendar reality of an Indian engineering student: 25–50 minute blocks, phone in another room, paper first then laptop.
- If they asked for something you cannot do (a job, a miracle), translate it into the ground move that actually produces that outcome.
- Tone check: would a senior who got placed at a good product company text this at 10am? If it sounds like ChatGPT, rewrite it.
""".strip()


def build_mentorship_user_prompt(
    *,
    first_name: str,
    college: str | None,
    department: str | None,
    today: str,
    yesterday: str,
    yesterday_notes: list[dict[str, Any]],
    open_older_notes: list[dict[str, Any]],
    recently_resolved: list[dict[str, Any]],
    previous_mentorship: dict[str, Any] | None,
) -> str:
    lines = [
        f"Student first name: {first_name}",
        f"College: {college or 'unknown'}",
        f"Department: {department or 'unknown'}",
        f"Today (Asia/Kolkata): {today}",
        f"Yesterday (the notes you must treat as today's brief): {yesterday}",
        "",
        "YESTERDAY'S NOTES (primary — solve these):",
    ]
    if yesterday_notes:
        for note in yesterday_notes:
            lines.append(_fmt_note(note))
    else:
        lines.append("(none — they wrote nothing yesterday)")

    lines.append("")
    lines.append("STILL OPEN FROM BEFORE YESTERDAY (leftovers they have not peeled):")
    if open_older_notes:
        for note in open_older_notes:
            lines.append(_fmt_note(note))
    else:
        lines.append("(none)")

    lines.append("")
    lines.append("PEELED / SOLVED RECENTLY (do not re-open these — they are done):")
    if recently_resolved:
        for note in recently_resolved:
            peeled = note.get("resolved_at") or "recently"
            lines.append(f"- id={note.get('id')} peeled={peeled} :: {note.get('body')}")
    else:
        lines.append("(none peeled recently)")

    lines.append("")
    lines.append("PREVIOUS MORNING DROP (do not copy it; only continue if they ignored it):")
    if previous_mentorship:
        lines.append(f"date: {previous_mentorship.get('mentorship_date')}")
        lines.append(f"headline: {previous_mentorship.get('headline')}")
        lines.append(f"diagnosis: {previous_mentorship.get('diagnosis')}")
        actions = previous_mentorship.get("actions") or []
        for action in actions[:4]:
            lines.append(
                f"- action {action.get('order')}: {action.get('title')} :: {action.get('do_exactly')}"
            )
    else:
        lines.append("(first morning drop)")

    lines.append("")
    lines.append("Write today's mentorship JSON now.")
    return "\n".join(lines)


def _fmt_note(note: dict[str, Any]) -> str:
    return (
        f"- id={note.get('id')} date={note.get('board_date')} "
        f"status={note.get('status')} :: {note.get('body')}"
    )

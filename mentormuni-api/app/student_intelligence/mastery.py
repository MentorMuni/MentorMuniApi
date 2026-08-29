"""Topic mastery updates — parity with Frontend topicMastery.js."""

from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Any

MODALITIES = ["recognition", "application", "explanation"]

TOOL_MODALITY = {
    "aptitude": "recognition",
    "skill_readiness": "recognition",
    "interview_readiness": "recognition",
    "coding": "application",
    "pseudocode": "application",
    "skill_mock": "explanation",
    "project_mock": "explanation",
    "interview_mock": "explanation",
    "hr_mock": "explanation",
    "resume_ats": "recognition",
}


def init_topic_mastery(topic_id: str) -> dict[str, Any]:
    return {
        "topic_id": topic_id,
        "modalities": {
            m: {"level": 0, "lastAttemptAt": None, "consecutivePasses": 0, "attempts": 0}
            for m in MODALITIES
        },
        "assessedAt": None,
        "nextReviewAt": None,
        "isDueForReview": False,
    }


def row_to_mastery(row: Any, today: date | None = None) -> dict[str, Any]:
    mastery = {
        "topic_id": row.topic_id,
        "modalities": {
            "recognition": {
                "level": row.recognition_level,
                "lastAttemptAt": row.recognition_last_at.isoformat()
                if row.recognition_last_at
                else None,
                "consecutivePasses": row.recognition_consecutive_passes,
                "attempts": row.recognition_attempts,
            },
            "application": {
                "level": row.application_level,
                "lastAttemptAt": row.application_last_at.isoformat()
                if row.application_last_at
                else None,
                "consecutivePasses": row.application_consecutive_passes,
                "attempts": row.application_attempts,
            },
            "explanation": {
                "level": row.explanation_level,
                "lastAttemptAt": row.explanation_last_at.isoformat()
                if row.explanation_last_at
                else None,
                "consecutivePasses": row.explanation_consecutive_passes,
                "attempts": row.explanation_attempts,
            },
        },
        "assessedAt": row.assessed_at.isoformat() if row.assessed_at else None,
        "nextReviewAt": row.next_review_at.isoformat() if row.next_review_at else None,
    }
    mastery["isDueForReview"] = is_due_for_review(mastery, today or date.today())
    return mastery


def update_mastery(
    mastery: dict[str, Any],
    *,
    modality: str,
    accuracy: float,
    within_time: bool,
    attempted_at: str,
) -> dict[str, Any]:
    if modality not in MODALITIES:
        raise ValueError(f"Invalid modality: {modality}")
    state = mastery["modalities"][modality]
    old_level = state["level"]
    state["attempts"] += 1
    state["lastAttemptAt"] = attempted_at
    passed = accuracy >= 0.6

    if passed:
        new_level = old_level
        if old_level in (0, 1):
            new_level = 2
            state["consecutivePasses"] = 1
        elif old_level == 2:
            if accuracy >= 0.75 and within_time:
                new_level = 3
                state["consecutivePasses"] = 1
            else:
                state["consecutivePasses"] += 1
        elif old_level == 3:
            if accuracy >= 0.85 and within_time:
                state["consecutivePasses"] += 1
                if state["consecutivePasses"] >= 2:
                    new_level = 4
            else:
                state["consecutivePasses"] = 0
        elif old_level == 4:
            state["consecutivePasses"] += 1
        state["level"] = new_level
    else:
        if old_level == 0:
            state["level"] = 1
        elif old_level in (1, 2):
            state["level"] = old_level
        elif old_level >= 3:
            state["level"] = max(2, old_level - 1)
        state["consecutivePasses"] = 0

    mastery["assessedAt"] = attempted_at
    return mastery


def is_due_for_review(mastery: dict[str, Any], today: date) -> bool:
    mods = mastery.get("modalities") or {}
    max_level = max((mods.get(m) or {}).get("level") or 0 for m in MODALITIES)
    if max_level < 3:
        return False
    nxt = mastery.get("nextReviewAt") or mastery.get("next_review_at")
    if not nxt:
        return True
    if isinstance(nxt, str):
        nxt = date.fromisoformat(nxt[:10])
    return nxt <= today


def schedule_next_review(mastery: dict[str, Any], today: date | None = None) -> str:
    today = today or date.today()
    mods = mastery.get("modalities") or {}
    max_level = max((mods.get(m) or {}).get("level") or 0 for m in MODALITIES)
    if max_level >= 4:
        delta = 14
    elif max_level >= 3:
        delta = 7
    else:
        delta = 3
    nxt = (today + timedelta(days=delta)).isoformat()
    mastery["nextReviewAt"] = nxt
    return nxt


def apply_mastery_to_row(row: Any, mastery: dict[str, Any]) -> None:
    for modality in MODALITIES:
        state = mastery["modalities"][modality]
        setattr(row, f"{modality}_level", state["level"])
        setattr(row, f"{modality}_attempts", state["attempts"])
        setattr(row, f"{modality}_consecutive_passes", state["consecutivePasses"])
        last = state.get("lastAttemptAt")
        if last:
            try:
                setattr(
                    row,
                    f"{modality}_last_at",
                    datetime.fromisoformat(str(last).replace("Z", "+00:00")),
                )
            except Exception:
                pass
    if mastery.get("assessedAt"):
        try:
            row.assessed_at = datetime.fromisoformat(
                str(mastery["assessedAt"]).replace("Z", "+00:00")
            )
        except Exception:
            pass
    nxt = mastery.get("nextReviewAt")
    if nxt:
        row.next_review_at = date.fromisoformat(str(nxt)[:10])

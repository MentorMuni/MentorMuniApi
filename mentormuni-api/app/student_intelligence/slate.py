"""Coverage ledger + slate selector — parity with Frontend intelligence modules."""

from __future__ import annotations

import math
from datetime import date, datetime
from typing import Any

POOL_DISTRIBUTION = {
    "arcA": {"NEW": 0.7, "RETRY": 0.25, "VERIFY": 0.05},
    "arcB": {"NEW": 0.4, "RETRY": 0.4, "VERIFY": 0.2},
    "arcC": {"NEW": 0.2, "RETRY": 0.4, "VERIFY": 0.4},
}


def get_arc(day_in_plan: int) -> str:
    if day_in_plan <= 14:
        return "arcA"
    if day_in_plan <= 29:
        return "arcB"
    return "arcC"


def get_pool_distribution(day_in_plan: int) -> dict[str, float]:
    return POOL_DISTRIBUTION[get_arc(day_in_plan)]


def init_coverage_ledger() -> dict[str, Any]:
    return {"tested": {}, "in_retry": set(), "in_verify": set()}


def ledger_from_rows(rows: list[Any]) -> dict[str, Any]:
    ledger = init_coverage_ledger()
    for row in rows:
        topic_id = row.topic_id
        ledger["tested"][topic_id] = {
            "pool": row.pool,
            "firstTestedAt": row.first_tested_at.isoformat() if row.first_tested_at else None,
            "lastTestedAt": row.last_tested_at.isoformat() if row.last_tested_at else None,
            "attempts": row.attempts,
            "correct": row.correct,
            "neverReturnToNEW": bool(row.never_return_to_new),
        }
        if row.pool == "RETRY":
            ledger["in_retry"].add(topic_id)
        if row.pool == "VERIFY":
            ledger["in_verify"].add(topic_id)
    return ledger


def can_retest_topic(ledger: dict[str, Any], topic_id: str) -> bool:
    entry = ledger["tested"].get(topic_id)
    if not entry:
        return True
    if entry["pool"] == "VERIFY":
        return False
    return True


def _days_difference(d1: datetime | date | str | None, d2: datetime | date | None = None) -> int:
    if not d1:
        return 999
    try:
        if isinstance(d1, str):
            d1 = datetime.fromisoformat(d1.replace("Z", "+00:00"))
        if isinstance(d1, datetime):
            d1 = d1.date() if d1.tzinfo is None else d1.replace(tzinfo=None).date()
        now = d2.date() if isinstance(d2, datetime) else (d2 or date.today())
        return abs((now - d1).days)
    except Exception:
        return 999


def select_slate(
    *,
    day_in_plan: int,
    num_questions_needed: int = 1,
    ledger: dict[str, Any],
    topic_mastery: dict[str, Any],
    pruned_syllabus: list[str],
    recent_questions: list[Any] | None = None,
) -> list[str]:
    if ledger is None or topic_mastery is None or pruned_syllabus is None:
        raise ValueError("select_slate: missing required parameters")

    dist = get_pool_distribution(day_in_plan)
    from_new = math.ceil(num_questions_needed * dist["NEW"])
    from_retry = math.ceil(num_questions_needed * dist["RETRY"])
    from_verify = math.ceil(num_questions_needed * dist["VERIFY"])

    new_topics = [t for t in pruned_syllabus if t not in ledger["tested"]]
    retry_topics = [
        t
        for t in pruned_syllabus
        if ledger["tested"].get(t)
        and ledger["tested"][t]["pool"] == "RETRY"
        and can_retest_topic(ledger, t)
    ]
    verify_topics = [
        t
        for t in pruned_syllabus
        if ledger["tested"].get(t)
        and ledger["tested"][t]["pool"] == "VERIFY"
        and (topic_mastery.get(t) or {}).get("isDueForReview")
    ]

    slate: list[str] = []
    slate.extend(_select_from_pool(new_topics, from_new, topic_mastery))
    slate.extend(_select_from_pool(retry_topics, from_retry, topic_mastery))
    slate.extend(_select_from_pool(verify_topics, from_verify, topic_mastery))

    if len(slate) < num_questions_needed:
        all_available = [
            t for t in retry_topics + new_topics + verify_topics if t not in slate
        ]
        slate.extend(
            _select_from_pool(
                all_available, num_questions_needed - len(slate), topic_mastery
            )
        )

    return slate[:num_questions_needed]


def _select_from_pool(
    candidates: list[str], num_needed: int, topic_mastery: dict[str, Any]
) -> list[str]:
    if not candidates or num_needed <= 0:
        return []
    scored = []
    for topic_id in candidates:
        mastery = topic_mastery.get(topic_id) or {}
        mods = mastery.get("modalities") or {}
        level = max(
            (mods.get("recognition") or {}).get("level") or 0,
            (mods.get("application") or {}).get("level") or 0,
            (mods.get("explanation") or {}).get("level") or 0,
        )
        last_ago = _days_difference(mastery.get("assessedAt") or mastery.get("assessed_at"))
        priority = (10 - level) * 1000 + last_ago * 10
        scored.append((priority, topic_id))
    scored.sort(key=lambda x: x[0])
    return [t for _, t in scored[:num_needed]]


def cosine_similarity(a: list[float], b: list[float]) -> float:
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    mag_a = math.sqrt(sum(x * x for x in a))
    mag_b = math.sqrt(sum(y * y for y in b))
    if mag_a == 0 or mag_b == 0:
        return 0.0
    return dot / (mag_a * mag_b)


def is_similar_to_recent(
    embedding: list[float] | None,
    recent_embeddings: list[dict[str, Any]] | None,
    threshold: float = 0.85,
) -> bool:
    if not embedding or not recent_embeddings:
        return False
    for recent in recent_embeddings:
        if cosine_similarity(embedding, recent.get("embedding") or []) >= threshold:
            return True
    return False

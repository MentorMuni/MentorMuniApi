"""Syllabus topics — parity with Frontend syllabus/map.js getAllTopics()."""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any


@lru_cache(maxsize=1)
def get_all_topics() -> list[dict[str, Any]]:
    path = Path(__file__).with_name("syllabus_topics.json")
    return json.loads(path.read_text(encoding="utf-8"))


def prune_syllabus_for_companies(
    all_topics: list[dict[str, Any]] | None,
    companies: list[str] | None,
) -> list[str]:
    topics = all_topics if all_topics is not None else get_all_topics()
    if not companies:
        return [t["id"] for t in topics]
    company_set = {str(c).lower() for c in companies}
    return [
        t["id"]
        for t in topics
        if any(str(c).lower() in company_set for c in (t.get("companies") or []))
    ]

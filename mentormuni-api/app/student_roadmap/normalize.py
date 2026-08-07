"""Normalize tool completion payloads into common analysis columns."""

from __future__ import annotations

from typing import Any


def _as_str_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        s = value.strip()
        return [s] if s else []
    if not isinstance(value, list):
        return []
    out: list[str] = []
    for item in value:
        if isinstance(item, str):
            s = item.strip()
            if s:
                out.append(s)
        elif isinstance(item, dict):
            topic = item.get("topic") or item.get("label") or item.get("text") or item.get("why")
            if topic:
                out.append(str(topic).strip())
    return out


def flatten_recommendations(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        out: list[str] = []
        for item in value:
            if isinstance(item, str) and item.strip():
                out.append(item.strip())
            elif isinstance(item, dict):
                topic = str(item.get("topic") or "").strip()
                why = str(item.get("why") or "").strip()
                if topic and why:
                    out.append(f"{topic}: {why}")
                elif topic:
                    out.append(topic)
                elif why:
                    out.append(why)
        return out
    return _as_str_list(value)


def normalize_complete_payload(body: dict[str, Any]) -> dict[str, Any]:
    score = body.get("score")
    if score is not None:
        try:
            score = float(score)
            score = max(0.0, min(100.0, score))
        except (TypeError, ValueError):
            score = None

    tech = body.get("technical_score")
    comm = body.get("communication_score")
    try:
        tech = int(tech) if tech is not None else None
    except (TypeError, ValueError):
        tech = None
    try:
        comm = int(comm) if comm is not None else None
    except (TypeError, ValueError):
        comm = None

    label = body.get("label")
    if label is not None:
        label = str(label).strip()[:255] or None

    return {
        "score": score,
        "label": label,
        "technical_score": tech,
        "communication_score": comm,
        "strengths": _as_str_list(body.get("strengths")),
        "weaknesses": _as_str_list(body.get("weaknesses")),
        "recommendations": flatten_recommendations(body.get("recommendations")),
        "raw": body.get("raw") if isinstance(body.get("raw"), dict) else body,
    }

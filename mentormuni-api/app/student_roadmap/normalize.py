"""Normalize tool completion payloads into common analysis columns.

Also hydrates voice/evaluate-shaped fields from nested `raw` so HOD/TPO
dashboards get technical/communication even when the FE only embeds analyze JSON.
"""

from __future__ import annotations

from typing import Any, Optional


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
            topic = (
                item.get("topic")
                or item.get("label")
                or item.get("text")
                or item.get("why")
                or item.get("name")
            )
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


def _clamp_score(value: Any) -> Optional[float]:
    if value is None:
        return None
    try:
        score = float(value)
        return max(0.0, min(100.0, score))
    except (TypeError, ValueError):
        return None


def _clamp_int_score(value: Any) -> Optional[int]:
    score = _clamp_score(value)
    if score is None:
        return None
    return int(round(score))


def extract_scores_from_raw(raw: Any) -> dict[str, Any]:
    """Pull score/tech/comm/strengths/gaps from nested analyze or evaluate payloads."""
    if not isinstance(raw, dict):
        return {}
    # Prefer nested analysis blocks commonly stored by FE
    nested = None
    for key in ("analysis", "result", "evaluate", "voice", "data", "payload"):
        if isinstance(raw.get(key), dict):
            nested = raw[key]
            break
    sources = [raw]
    if nested:
        sources.append(nested)

    out: dict[str, Any] = {}
    for src in sources:
        if out.get("score") is None:
            out["score"] = _clamp_score(
                src.get("score")
                if src.get("score") is not None
                else src.get("overall_score")
                if src.get("overall_score") is not None
                else src.get("readiness_percentage")
            )
        if out.get("label") is None:
            label = src.get("label") or src.get("readiness_label")
            if label is not None:
                out["label"] = str(label).strip()[:255] or None
        if out.get("technical_score") is None:
            out["technical_score"] = _clamp_int_score(src.get("technical_score"))
        if out.get("communication_score") is None:
            out["communication_score"] = _clamp_int_score(src.get("communication_score"))
        if not out.get("strengths"):
            strengths = _as_str_list(src.get("strengths"))
            if strengths:
                out["strengths"] = strengths
        if not out.get("weaknesses"):
            weaknesses = _as_str_list(src.get("weaknesses") or src.get("gaps"))
            if weaknesses:
                out["weaknesses"] = weaknesses
        if not out.get("recommendations"):
            recs = flatten_recommendations(
                src.get("recommendations")
                or src.get("learning_recommendations")
                or src.get("study_plan")
            )
            if recs:
                out["recommendations"] = recs

    # Derive overall from tech/comm when score missing (voice analyze shape)
    if out.get("score") is None:
        tech = out.get("technical_score")
        comm = out.get("communication_score")
        if tech is not None and comm is not None:
            out["score"] = round((float(tech) + float(comm)) / 2.0, 1)
        elif tech is not None:
            out["score"] = float(tech)
        elif comm is not None:
            out["score"] = float(comm)
    return out


def normalize_complete_payload(body: dict[str, Any]) -> dict[str, Any]:
    raw = body.get("raw") if isinstance(body.get("raw"), dict) else body
    hydrated = extract_scores_from_raw(raw if isinstance(raw, dict) else {})

    score = _clamp_score(body.get("score"))
    if score is None:
        score = hydrated.get("score")

    tech = _clamp_int_score(body.get("technical_score"))
    if tech is None:
        tech = hydrated.get("technical_score")

    comm = _clamp_int_score(body.get("communication_score"))
    if comm is None:
        comm = hydrated.get("communication_score")

    label = body.get("label")
    if label is not None:
        label = str(label).strip()[:255] or None
    if not label:
        label = hydrated.get("label")

    strengths = _as_str_list(body.get("strengths")) or hydrated.get("strengths") or []
    weaknesses = _as_str_list(body.get("weaknesses")) or hydrated.get("weaknesses") or []
    recommendations = (
        flatten_recommendations(body.get("recommendations"))
        or hydrated.get("recommendations")
        or []
    )

    return {
        "score": score,
        "label": label,
        "technical_score": tech,
        "communication_score": comm,
        "strengths": strengths,
        "weaknesses": weaknesses,
        "recommendations": recommendations,
        "raw": raw if isinstance(raw, dict) else body,
    }

"""computeReadiness — byte-parity with Frontend readiness/readinessScore.js."""

from __future__ import annotations

import math
from datetime import datetime
from typing import Any

PILLARS = ["aptitude", "coding", "technical", "communication", "hr", "resume"]

PILLAR_LABELS = {
    "aptitude": "Aptitude",
    "coding": "Coding",
    "technical": "Technical",
    "communication": "Communication",
    "hr": "HR / behavioural",
    "resume": "Resume",
}

WEIGHTS_BY_TIER = {
    "mass_recruiter": {
        "aptitude": 0.26,
        "communication": 0.20,
        "technical": 0.18,
        "coding": 0.14,
        "hr": 0.12,
        "resume": 0.10,
    },
    "product": {
        "coding": 0.30,
        "technical": 0.24,
        "communication": 0.14,
        "aptitude": 0.12,
        "hr": 0.10,
        "resume": 0.10,
    },
}

TOOL_PILLARS = {
    "aptitude": {"aptitude": 1},
    "pseudocode": {"coding": 0.6, "technical": 0.4},
    "coding": {"coding": 1},
    "skill_readiness": {"technical": 1},
    "skill_mock": {"technical": 0.6, "communication": 0.4},
    "project_mock": {"technical": 0.5, "communication": 0.5},
    "interview_readiness": {"technical": 0.7, "communication": 0.3},
    "interview_mock": {"technical": 0.5, "communication": 0.5},
    "hr_mock": {"hr": 0.7, "communication": 0.3},
    "hr_bank": {"hr": 1},
    "written_round": {"communication": 0.8, "technical": 0.2},
    "ms_office": {"technical": 1},
    "resume_ats": {"resume": 1},
}

HALF_LIFE_DAYS = 30
DECAY_FLOOR = 0.6
DEFAULT_TARGET = 85

GATES = [
    {"id": "tcs_ninja", "company": "TCS", "label": "TCS Ninja", "overall": 50, "pillars": {"aptitude": 55, "communication": 45}},
    {"id": "tcs_digital", "company": "TCS", "label": "TCS Digital", "overall": 65, "pillars": {"aptitude": 65, "coding": 60, "technical": 60}},
    {"id": "tcs_prime", "company": "TCS", "label": "TCS Prime", "overall": 78, "pillars": {"coding": 75, "technical": 75, "aptitude": 70}},
    {"id": "infosys_dse", "company": "Infosys", "label": "Infosys DSE", "overall": 55, "pillars": {"coding": 55, "aptitude": 55}},
    {"id": "infosys_sp", "company": "Infosys", "label": "Infosys SP", "overall": 70, "pillars": {"coding": 70, "technical": 62}},
    {"id": "accenture", "company": "Accenture", "label": "Accenture", "overall": 60, "pillars": {"communication": 60, "aptitude": 58}},
    {"id": "wipro", "company": "Wipro", "label": "Wipro Elite", "overall": 55, "pillars": {"aptitude": 55, "communication": 55}},
    {"id": "cognizant", "company": "Cognizant", "label": "Cognizant GenC", "overall": 58, "pillars": {"aptitude": 58, "technical": 55}},
    {"id": "capgemini", "company": "Capgemini", "label": "Capgemini", "overall": 55, "pillars": {"aptitude": 58, "coding": 50}},
]


def pillar_weights(target_tier: str = "mass_recruiter") -> dict[str, float]:
    return WEIGHTS_BY_TIER.get(target_tier) or WEIGHTS_BY_TIER["mass_recruiter"]


def recency_weight(age_days: float) -> float:
    age = max(0.0, float(age_days or 0))
    return DECAY_FLOOR + (1 - DECAY_FLOOR) * (2 ** (-age / HALF_LIFE_DAYS))


def _age_in_days(completed_at: Any, today: str | None) -> int:
    if not completed_at or not today:
        return 0
    try:
        if isinstance(completed_at, datetime):
            then = completed_at
        else:
            then = datetime.fromisoformat(str(completed_at).replace("Z", "+00:00"))
        now = datetime.fromisoformat(f"{today}T00:00:00")
        if then.tzinfo:
            then = then.replace(tzinfo=None)
        return max(0, round((now - then).total_seconds() / 86400))
    except Exception:
        return 0


def _estimate_eta_days(sorted_attempts: list[dict], overall: int, target: int, today: str | None):
    if overall >= target:
        return 0
    recent = [a for a in sorted_attempts if _age_in_days(a.get("completed_at"), today) <= 14]
    if len(recent) < 2:
        return None
    first = float(recent[0]["score"])
    last = float(recent[-1]["score"])
    span = max(1, _age_in_days(recent[0].get("completed_at"), today))
    per_day = (last - first) / span
    if not math.isfinite(per_day) or per_day <= 0:
        return None
    return min(180, max(7, round((target - overall) / per_day)))


def gates_for(readiness: dict[str, Any], target_companies: list[str] | None = None) -> list[dict]:
    wanted = {str(c).lower() for c in (target_companies or [])}
    relevant = (
        [g for g in GATES if g["company"].lower() in wanted] if wanted else list(GATES)
    )
    out = []
    for gate in relevant:
        blockers = []
        if readiness["overall"] < gate["overall"]:
            blockers.append(
                {"pillar": "overall", "need": gate["overall"], "have": readiness["overall"]}
            )
        for pillar, need in gate["pillars"].items():
            have = (readiness.get("pillars") or {}).get(pillar)
            if not have or not have.get("hasData"):
                blockers.append({"pillar": pillar, "need": need, "have": None, "unmeasured": True})
            elif have["score"] < need:
                blockers.append(
                    {
                        "pillar": pillar,
                        "need": need,
                        "have": have["score"],
                        "gap": need - have["score"],
                    }
                )
        with_gap = [b for b in blockers if b.get("gap") is not None]
        binding = sorted(with_gap, key=lambda b: b["gap"], reverse=True)[0] if with_gap else (
            blockers[0] if blockers else None
        )
        out.append(
            {
                "id": gate["id"],
                "company": gate["company"],
                "label": gate["label"],
                "cleared": len(blockers) == 0,
                "blockers": blockers,
                "binding_constraint": binding,
            }
        )
    return out


def compute_readiness(input_data: dict[str, Any] | None = None) -> dict[str, Any]:
    """Identical algorithm to Frontend computeReadiness()."""
    data = input_data or {}
    attempts = data.get("attempts") or []
    today = data.get("today")
    completion_rate_7d = data.get("completionRate7d", data.get("completion_rate_7d", 0))
    target_tier = data.get("targetTier", data.get("target_tier", "mass_recruiter"))
    target_companies = data.get("targetCompanies", data.get("target_companies")) or []
    target = data.get("target", DEFAULT_TARGET)

    weights = pillar_weights(target_tier)
    acc: dict[str, dict[str, Any]] = {
        p: {"weighted": 0.0, "weight": 0.0, "scores": [], "attempts": 0, "lastAt": None}
        for p in PILLARS
    }

    sorted_attempts = sorted(
        [
            a
            for a in attempts
            if a and a.get("score") is not None and TOOL_PILLARS.get(a.get("tool_code"))
        ],
        key=lambda a: str(a.get("completed_at") or ""),
    )

    for attempt in sorted_attempts:
        contributions = TOOL_PILLARS[attempt["tool_code"]]
        age = _age_in_days(attempt.get("completed_at"), today)
        recency = recency_weight(age)
        for pillar, share in contributions.items():
            score = float(attempt["score"])
            if pillar == "technical" and attempt.get("technical_score") is not None:
                score = float(attempt["technical_score"])
            if pillar == "communication" and attempt.get("communication_score") is not None:
                score = float(attempt["communication_score"])
            if not math.isfinite(score):
                continue
            w = share * recency
            acc[pillar]["weighted"] += score * w
            acc[pillar]["weight"] += w
            acc[pillar]["scores"].append(score)
            acc[pillar]["attempts"] += 1
            acc[pillar]["lastAt"] = attempt.get("completed_at") or acc[pillar]["lastAt"]

    pillars: dict[str, Any] = {}
    measured_count = 0
    for p in PILLARS:
        a = acc[p]
        has_data = a["weight"] > 0
        if has_data:
            measured_count += 1
        scores = a["scores"]
        latest = scores[-1] if scores else None
        previous = scores[-2] if len(scores) > 1 else None
        pillars[p] = {
            "label": PILLAR_LABELS[p],
            "score": round(a["weighted"] / a["weight"]) if has_data else 0,
            "hasData": has_data,
            "attempts": a["attempts"],
            "confidence": min(1.0, a["attempts"] / 2),
            "trend": round(latest - previous) if previous is not None else None,
            "last_at": a["lastAt"],
            "weight": weights[p],
        }

    weight_sum = 0.0
    score_sum = 0.0
    for p in PILLARS:
        if not pillars[p]["hasData"]:
            continue
        weight_sum += weights[p]
        score_sum += pillars[p]["score"] * weights[p]
    base = score_sum / weight_sum if weight_sum > 0 else 0.0

    rate = min(1.0, max(0.0, float(completion_rate_7d or 0)))
    execution = 0.9 + 0.1 * rate
    overall = round(base * execution)

    measured = [p for p in PILLARS if pillars[p]["hasData"]]
    weakest = None
    if measured:
        weakest = measured[0]
        for p in measured[1:]:
            if pillars[p]["score"] < pillars[weakest]["score"]:
                weakest = p
    unmeasured = next((p for p in PILLARS if not pillars[p]["hasData"]), None)

    result = {
        "overall": overall,
        "base": round(base),
        "execution_multiplier": round(execution * 100) / 100,
        "coverage": measured_count / len(PILLARS),
        "measured_pillars": measured_count,
        "total_pillars": len(PILLARS),
        "target": target,
        "target_tier": target_tier,
        "eta_days": _estimate_eta_days(sorted_attempts, overall, target, today),
        "pillars": pillars,
        "focus_pillar": unmeasured or weakest,
        "weakest_pillar": weakest,
        "gates": [],
        "computed_at": today,
    }
    result["gates"] = gates_for(result, target_companies)
    return result

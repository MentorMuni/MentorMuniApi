"""Validate / normalize Company Intelligence JSON from the LLM."""

from __future__ import annotations

from typing import Any


class CompanyIntelValidationError(ValueError):
    pass


FORBIDDEN_KEYS = {
    "interview_questions",
    "sample_questions",
    "questions",
    "study_plan",
    "preparation_plan",
    "learning_plan",
    "roadmap",
}


def _strip_forbidden(obj: Any) -> Any:
    if isinstance(obj, dict):
        out = {}
        for k, v in obj.items():
            key = str(k).strip().lower()
            if key in FORBIDDEN_KEYS:
                continue
            out[k] = _strip_forbidden(v)
        return out
    if isinstance(obj, list):
        return [_strip_forbidden(x) for x in obj]
    return obj


def _as_float(v: Any) -> float | None:
    try:
        if v is None or v == "" or v == "Unknown":
            return None
        return float(v)
    except (TypeError, ValueError):
        return None


def validate_company_intelligence(plan: Any, *, company: str, role: str, country: str) -> dict[str, Any]:
    if not isinstance(plan, dict):
        raise CompanyIntelValidationError("payload must be a JSON object")

    root = _strip_forbidden(plan)
    root["company"] = str(root.get("company") or company).strip() or company
    root["role"] = str(root.get("role") or role).strip() or role
    root["country"] = str(root.get("country") or country).strip() or country

    meta = root.get("metadata")
    if not isinstance(meta, dict):
        meta = {}
        root["metadata"] = meta

    conf = _as_float(meta.get("overall_confidence"))
    if conf is None:
        # Fall back to company_profile confidence if present
        profile = root.get("company_profile") if isinstance(root.get("company_profile"), dict) else {}
        conf = _as_float(profile.get("confidence"))
    if conf is not None:
        conf = max(0.0, min(1.0, conf))
        meta["overall_confidence"] = conf

    strength = meta.get("evidence_strength")
    if strength not in ("Very High", "High", "Medium", "Low", "Unknown", None, ""):
        meta["evidence_strength"] = "Unknown"
    elif not strength:
        meta["evidence_strength"] = "Unknown"

    # Soft unknowns when overall confidence is weak
    if conf is not None and conf < 0.50:
        meta["evidence_strength"] = meta.get("evidence_strength") or "Low"

    if not isinstance(root.get("hiring_process"), list):
        root["hiring_process"] = []
    if not isinstance(root.get("evaluation_dimensions"), list):
        root["evaluation_dimensions"] = []
    if not isinstance(root.get("common_rejection_reasons"), list):
        root["common_rejection_reasons"] = []
    if not isinstance(root.get("mock_interview_blueprint"), list):
        root["mock_interview_blueprint"] = []
    if not isinstance(root.get("topic_frequency"), (dict, list)):
        root["topic_frequency"] = {}
    if not isinstance(root.get("interview_profile"), dict):
        root["interview_profile"] = {}
    if not isinstance(root.get("project_evaluation"), dict):
        root["project_evaluation"] = {}
    if not isinstance(root.get("company_profile"), dict):
        root["company_profile"] = {}

    # Cap rejection reasons
    reasons = root["common_rejection_reasons"]
    if isinstance(reasons, list) and len(reasons) > 10:
        root["common_rejection_reasons"] = reasons[:10]

    return root

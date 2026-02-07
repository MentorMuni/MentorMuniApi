"""
Simple stats and lead capture for Interview Ready.
In-memory counter; leads logged. Upgrade to Redis/DB for production scale.
"""
import json
import logging
import os
from pathlib import Path
from typing import Optional

logger = logging.getLogger("stats_service")

# In-memory counters (resets on deploy; use Redis/DB for persistence)
_total_checks: int = 0
_total_views: int = 0
_leads_path: Optional[Path] = None


def _leads_file() -> Path:
    global _leads_path
    if _leads_path is None:
        base = Path(os.environ.get("DATA_DIR", "/tmp"))
        try:
            base.mkdir(parents=True, exist_ok=True)
        except OSError:
            base = Path("/tmp")
        _leads_path = base / "interview_ready_leads.jsonl"
    return _leads_path


def increment_checks() -> int:
    """Increment and return total readiness checks completed."""
    global _total_checks
    _total_checks += 1
    return _total_checks


def increment_views() -> int:
    """Increment and return total page views (link hits)."""
    global _total_views
    _total_views += 1
    return _total_views


def get_stats() -> dict:
    return {"total_checks": _total_checks, "total_views": _total_views}


def get_leads(limit: int = 1000) -> list:
    """Read recent leads from JSONL file. Admin use only."""
    path = _leads_file()
    if not path.exists():
        return []
    lines = path.read_text(encoding="utf-8").strip().split("\n")
    lines = [l for l in lines if l.strip()][-limit:]
    out = []
    for line in lines:
        try:
            out.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return out[::-1]  # newest first


def store_lead(email: Optional[str], phone: Optional[str], profile: Optional[dict]) -> None:
    """Append lead to JSONL file (non-blocking, best-effort)."""
    if not email and not phone:
        return
    try:
        line = json.dumps({
            "email": (email or "").strip() or None,
            "phone": (phone or "").strip() or None,
            "user_type": profile.get("user_type") if profile else None,
            "primary_skill": profile.get("primary_skill") if profile else None,
            "target_role": profile.get("target_role") if profile else None,
        }, ensure_ascii=False) + "\n"
        with open(_leads_file(), "a", encoding="utf-8") as f:
            f.write(line)
        logger.info("Lead captured: email=%s phone=%s", bool(email), bool(phone))
    except Exception as e:
        logger.warning("Could not store lead: %s", e)

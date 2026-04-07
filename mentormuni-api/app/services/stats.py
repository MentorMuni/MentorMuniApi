"""
Simple stats and lead capture for Interview Ready.
In-memory counter; leads logged. Upgrade to Redis/DB for production scale.
"""
import json
import logging
import os
from pathlib import Path
from typing import Any, Optional

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


def get_leads(limit: Optional[int] = None) -> list:
    """
    Read leads from JSONL (each line = one JSON object). Newest first.
    If limit is None or <= 0, returns every parseable row in the file.
    If limit > 0, returns at most that many of the most recent rows.
    """
    path = _leads_file()
    if not path.exists():
        return []
    raw = path.read_text(encoding="utf-8")
    if not raw.strip():
        return []
    lines = [ln for ln in raw.split("\n") if ln.strip()]
    if limit is not None and limit > 0:
        lines = lines[-limit:]
    out: list = []
    for line in lines:
        try:
            out.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return out[::-1]  # newest first


def append_interview_ready_lead(record: dict[str, Any]) -> None:
    """Append one Interview Ready lead object (full JSON shape) to JSONL."""
    try:
        line = json.dumps(record, ensure_ascii=False) + "\n"
        with open(_leads_file(), "a", encoding="utf-8") as f:
            f.write(line)
        logger.info(
            "Lead captured: email=%s phone=%s",
            bool(record.get("email")),
            bool(record.get("phone")),
        )
    except Exception as e:
        logger.warning("Could not store lead: %s", e)

"""
File-based storage for contact/enroll submissions.
Uses JSONL (one JSON object per line) for easy append and parsing.
"""
import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

logger = logging.getLogger("contact_storage")

_DATA_DIR = os.environ.get("DATA_DIR", "/tmp")
_FILE: Optional[Path] = None


def _file_path() -> Path:
    global _FILE
    if _FILE is None:
        base = Path(_DATA_DIR)
        try:
            base.mkdir(parents=True, exist_ok=True)
        except OSError:
            base = Path("/tmp")
        _FILE = base / "contact_submissions.jsonl"
    return _FILE


def store_submission(data: dict) -> None:
    """
    Append a submission to the JSONL file.
    Thread-safe for single-process; use file lock for multi-worker if needed.
    """
    entry = {
        "ts": datetime.now(timezone.utc).isoformat(),
        **{k: v for k, v in data.items() if v is not None and str(v).strip()},
    }
    line = json.dumps(entry, ensure_ascii=False) + "\n"
    try:
        with open(_file_path(), "a", encoding="utf-8") as f:
            f.write(line)
        logger.info("Contact stored: email=%s", data.get("email", ""))
    except Exception as e:
        logger.warning("Could not store contact: %s", e)
        raise


def get_submissions(limit: int = 1000) -> list[dict]:
    """Read recent submissions (last N lines). Admin use only."""
    path = _file_path()
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

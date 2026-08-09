"""Pytest configuration for coding Phase 3 tests."""

from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

# mentormuni-api/ on path
_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))


def pytest_configure(config: pytest.Config) -> None:
    config.addinivalue_line("markers", "integration: requires reachable PostgreSQL")


@pytest.fixture(scope="session")
def database_url() -> str | None:
    url = (os.getenv("TEST_DATABASE_URL") or os.getenv("DATABASE_URL") or "").strip()
    return url or None

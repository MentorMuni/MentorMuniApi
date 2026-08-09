"""Factory for CodeExecutionService / providers."""

from __future__ import annotations

from functools import lru_cache

from app.coding.execution.judge0 import Judge0Provider
from app.coding.execution.local_python import LocalPythonProvider
from app.coding.execution.service import CodeExecutionService
from app.core.config import settings


@lru_cache
def get_code_execution_service() -> CodeExecutionService:
    provider_name = (getattr(settings, "coding_execution_provider", None) or "judge0").lower()
    judge0_url = (settings.judge0_base_url or "").strip()

    if provider_name == "local_python" or (
        not judge0_url and str(getattr(settings, "app_env", "")).lower() in {"development", "dev", "local"}
    ):
        return CodeExecutionService(provider=LocalPythonProvider())  # type: ignore[arg-type]

    if provider_name != "judge0":
        raise RuntimeError(f"Unsupported coding execution provider: {provider_name}")

    return CodeExecutionService(provider=Judge0Provider())

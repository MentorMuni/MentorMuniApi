"""Code execution provider protocol."""

from __future__ import annotations

from typing import Any, Awaitable, Callable, Optional, Protocol

from app.coding.execution.types import ExecuteRequest, SingleExecutionResult

ProviderUpdateCallback = Callable[[str, Optional[str], Optional[str]], Awaitable[None]]


class CodeExecutionProvider(Protocol):
    """Adapter interface — Judge0-specific details stay inside the adapter."""

    name: str

    async def execute_one(
        self,
        *,
        source_code: str,
        language_id: int,
        stdin: str,
        expected_output: str | None,
        cpu_time_limit_s: float,
        wall_time_limit_s: float,
        memory_limit_kb: int,
        max_stdout_bytes: int,
        on_provider_update: ProviderUpdateCallback | None = None,
    ) -> SingleExecutionResult:
        """Compile/run one program against one stdin; never runs in FastAPI process."""
        ...

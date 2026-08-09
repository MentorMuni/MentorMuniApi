"""Local Python subprocess executor for development when Judge0 is not configured.

ONLY used when APP_ENV=development and JUDGE0_BASE_URL is empty.
Runs student Python in a short-lived subprocess (not a full sandbox).
C++/Java return a clear provider error — configure Judge0 for those languages.
"""

from __future__ import annotations

import asyncio
import logging
import tempfile
from pathlib import Path
from typing import Awaitable, Callable, Optional

from app.coding.enums import TestResultStatus, Verdict
from app.coding.execution.judge0 import outputs_match
from app.coding.execution.types import SingleExecutionResult

logger = logging.getLogger("coding.local_python")

ProviderUpdateCallback = Callable[[str, Optional[str], Optional[str]], Awaitable[None]]

# Judge0 language ids used in our seed
_PYTHON_LANG_IDS = {71, 92, 100, 109}  # common CE python3 ids


class LocalPythonProvider:
    name = "local_python"

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
        if language_id not in _PYTHON_LANG_IDS:
            return SingleExecutionResult(
                status=TestResultStatus.ERROR,
                verdict=None,
                error_type="provider_error",
                error_message=(
                    "Local executor only supports Python. "
                    "Set JUDGE0_BASE_URL for C++/Java, or switch language to Python."
                ),
                provider_status="unsupported_language",
            )

        if on_provider_update:
            await on_provider_update(self.name, None, "local_running")

        timeout = max(1.0, min(float(wall_time_limit_s or 2.0), 8.0))
        tmp_path: Path | None = None
        try:
            with tempfile.NamedTemporaryFile(
                mode="w", suffix=".py", delete=False, encoding="utf-8"
            ) as fh:
                fh.write(source_code)
                tmp_path = Path(fh.name)

            proc = await asyncio.create_subprocess_exec(
                "python3",
                str(tmp_path),
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            try:
                stdout_b, stderr_b = await asyncio.wait_for(
                    proc.communicate(input=(stdin or "").encode("utf-8", errors="replace")),
                    timeout=timeout,
                )
            except asyncio.TimeoutError:
                proc.kill()
                await proc.wait()
                return SingleExecutionResult(
                    status=TestResultStatus.ERROR,
                    verdict=Verdict.TIME_LIMIT_EXCEEDED,
                    error_type="time_limit_exceeded",
                    error_message="Local execution timed out",
                    provider_status="timeout",
                )

            stdout = (stdout_b or b"").decode("utf-8", errors="replace")[:max_stdout_bytes]
            stderr = (stderr_b or b"").decode("utf-8", errors="replace")[:max_stdout_bytes]
            code = proc.returncode or 0

            if code != 0:
                return SingleExecutionResult(
                    status=TestResultStatus.ERROR,
                    verdict=Verdict.RUNTIME_ERROR,
                    stdout=stdout,
                    stderr=stderr,
                    error_type="runtime_error",
                    error_message=f"Process exited with code {code}",
                    provider_status=str(code),
                )

            if expected_output is not None and not outputs_match(stdout, expected_output):
                return SingleExecutionResult(
                    status=TestResultStatus.FAILED,
                    verdict=Verdict.WRONG_ANSWER,
                    stdout=stdout,
                    stderr=stderr,
                    error_type="wrong_answer",
                    error_message="Output mismatch",
                    provider_status="done",
                )

            return SingleExecutionResult(
                status=TestResultStatus.PASSED,
                verdict=Verdict.ACCEPTED,
                stdout=stdout,
                stderr=stderr,
                provider_status="done",
            )
        except Exception as exc:  # noqa: BLE001
            logger.exception("local_python_exec_failed")
            return SingleExecutionResult(
                status=TestResultStatus.ERROR,
                verdict=None,
                error_type="provider_error",
                error_message=f"Local executor error: {type(exc).__name__}",
                provider_status="error",
            )
        finally:
            if tmp_path is not None:
                try:
                    tmp_path.unlink(missing_ok=True)
                except OSError:
                    pass

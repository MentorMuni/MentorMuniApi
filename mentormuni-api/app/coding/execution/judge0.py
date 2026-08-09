"""Judge0 Cloud/CE adapter — async create + poll; no Judge0 types leak upward."""

from __future__ import annotations

import asyncio
import logging
from typing import Any, Awaitable, Callable, Optional

import httpx

from app.coding.enums import TestResultStatus, Verdict
from app.coding.execution.types import SingleExecutionResult
from app.core.config import settings

logger = logging.getLogger("coding.judge0")

ProviderUpdateCallback = Callable[[str, Optional[str], Optional[str]], Awaitable[None]]

# Judge0 status_id → our verdict/status
_STATUS_MAP: dict[int, tuple[TestResultStatus, Optional[Verdict], Optional[str]]] = {
    3: (TestResultStatus.PASSED, Verdict.ACCEPTED, None),
    4: (TestResultStatus.FAILED, Verdict.WRONG_ANSWER, "wrong_answer"),
    5: (TestResultStatus.ERROR, Verdict.TIME_LIMIT_EXCEEDED, "time_limit_exceeded"),
    6: (TestResultStatus.ERROR, Verdict.COMPILATION_ERROR, "compilation_error"),
    7: (TestResultStatus.ERROR, Verdict.RUNTIME_ERROR, "runtime_error"),
    8: (TestResultStatus.ERROR, Verdict.RUNTIME_ERROR, "runtime_error"),
    9: (TestResultStatus.ERROR, Verdict.RUNTIME_ERROR, "runtime_error"),
    10: (TestResultStatus.ERROR, Verdict.RUNTIME_ERROR, "runtime_error"),
    11: (TestResultStatus.ERROR, Verdict.RUNTIME_ERROR, "runtime_error"),
    12: (TestResultStatus.ERROR, Verdict.RUNTIME_ERROR, "runtime_error"),
    13: (TestResultStatus.ERROR, None, "internal_error"),
    14: (TestResultStatus.ERROR, Verdict.RUNTIME_ERROR, "exec_format_error"),
    15: (TestResultStatus.ERROR, Verdict.RUNTIME_ERROR, "runtime_error"),
}


def _truncate(text: str | None, max_bytes: int) -> str:
    if not text:
        return ""
    raw = text.encode("utf-8", errors="replace")
    if len(raw) <= max_bytes:
        return text
    return raw[:max_bytes].decode("utf-8", errors="replace") + "\n…[truncated]"


def _normalize_output(text: str) -> str:
    return (text or "").replace("\r\n", "\n").rstrip("\n")


class Judge0Provider:
    name = "judge0"

    def __init__(
        self,
        *,
        base_url: str | None = None,
        api_key: str | None = None,
        poll_interval_ms: int | None = None,
        max_polls: int = 60,
    ) -> None:
        self.base_url = (base_url or settings.judge0_base_url or "").rstrip("/")
        self.api_key = api_key if api_key is not None else settings.judge0_api_key
        self.poll_interval_ms = poll_interval_ms or settings.coding_job_poll_interval_ms
        self.max_polls = max_polls

    def _headers(self) -> dict[str, str]:
        headers = {"Content-Type": "application/json", "Accept": "application/json"}
        if not self.api_key:
            return headers
        # RapidAPI Judge0 CE
        if "rapidapi" in self.base_url.lower():
            headers["X-RapidAPI-Key"] = self.api_key
            host = self.base_url.split("://", 1)[-1].split("/", 1)[0]
            headers["X-RapidAPI-Host"] = host
        else:
            headers["X-Auth-Token"] = self.api_key
        return headers

    def _ensure_configured(self) -> None:
        if not self.base_url:
            raise RuntimeError("JUDGE0_BASE_URL is not configured.")

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
        self._ensure_configured()
        payload: dict[str, Any] = {
            "source_code": source_code,
            "language_id": language_id,
            "stdin": stdin or "",
            "cpu_time_limit": max(0.1, float(cpu_time_limit_s)),
            "wall_time_limit": max(1.0, float(wall_time_limit_s)),
            "memory_limit": int(memory_limit_kb),
            "enable_network": False,
        }
        if expected_output is not None:
            payload["expected_output"] = expected_output

        token: str | None = None
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                create = await client.post(
                    f"{self.base_url}/submissions",
                    params={"base64_encoded": "false", "wait": "false"},
                    headers=self._headers(),
                    json=payload,
                )
                if create.status_code >= 400:
                    body = _truncate(create.text, 500)
                    logger.warning("judge0_create_failed status=%s body=%s", create.status_code, body)
                    return SingleExecutionResult(
                        status=TestResultStatus.ERROR,
                        verdict=None,
                        error_type="provider_error",
                        error_message=f"Judge0 create failed ({create.status_code})",
                        provider_status=str(create.status_code),
                    )
                data = create.json()
                token = str(data.get("token") or "")
                if not token:
                    return SingleExecutionResult(
                        status=TestResultStatus.ERROR,
                        verdict=None,
                        error_type="provider_error",
                        error_message="Judge0 returned no token",
                    )
                if on_provider_update:
                    await on_provider_update(self.name, token, "created")

                for _ in range(self.max_polls):
                    await asyncio.sleep(self.poll_interval_ms / 1000.0)
                    poll = await client.get(
                        f"{self.base_url}/submissions/{token}",
                        params={"base64_encoded": "false", "fields": "*"},
                        headers=self._headers(),
                    )
                    if poll.status_code >= 400:
                        if on_provider_update:
                            await on_provider_update(self.name, token, f"poll_error_{poll.status_code}")
                        continue
                    result = poll.json()
                    status_obj = result.get("status") or {}
                    status_id = int(status_obj.get("id") or 0)
                    status_desc = str(status_obj.get("description") or status_id)
                    if on_provider_update:
                        await on_provider_update(self.name, token, status_desc)
                    # 1=In Queue, 2=Processing
                    if status_id in (1, 2):
                        continue
                    return self._map_result(result, status_id, token, max_stdout_bytes)

                return SingleExecutionResult(
                    status=TestResultStatus.ERROR,
                    verdict=Verdict.TIME_LIMIT_EXCEEDED,
                    error_type="provider_timeout",
                    error_message="Timed out waiting for Judge0",
                    provider_token=token,
                    provider_status="poll_timeout",
                )
        except httpx.HTTPError as exc:
            logger.warning("judge0_http_error err=%s", type(exc).__name__)
            return SingleExecutionResult(
                status=TestResultStatus.ERROR,
                verdict=None,
                error_type="provider_error",
                error_message="Judge0 network error",
                provider_token=token,
            )

    def _map_result(
        self,
        result: dict[str, Any],
        status_id: int,
        token: str,
        max_stdout_bytes: int,
    ) -> SingleExecutionResult:
        stdout = _truncate(result.get("stdout"), max_stdout_bytes)
        stderr = _truncate(result.get("stderr"), max_stdout_bytes)
        compile_output = _truncate(result.get("compile_output"), max_stdout_bytes)
        message = _truncate(result.get("message"), 1000)

        time_s = result.get("time")
        execution_time_ms = None
        if time_s is not None:
            try:
                execution_time_ms = int(float(time_s) * 1000)
            except (TypeError, ValueError):
                execution_time_ms = None
        memory = result.get("memory")
        memory_used_kb = int(memory) if memory is not None else None

        mapped = _STATUS_MAP.get(status_id)
        if mapped is None:
            # Unknown terminal — treat as system/provider error
            return SingleExecutionResult(
                status=TestResultStatus.ERROR,
                verdict=None,
                stdout=stdout,
                stderr=stderr,
                compile_output=compile_output,
                message=message,
                execution_time_ms=execution_time_ms,
                memory_used_kb=memory_used_kb,
                provider_status=str(status_id),
                provider_token=token,
                error_type="provider_error",
                error_message=message or f"Unknown Judge0 status {status_id}",
            )

        status, verdict, error_type = mapped
        # If Judge0 reports Accepted, still compare normalized stdout when expected was sent
        # (Judge0 already compares when expected_output set; trust status_id=3)
        if status_id == 6:
            return SingleExecutionResult(
                status=status,
                verdict=verdict,
                stdout=stdout,
                stderr=stderr,
                compile_output=compile_output,
                message=message,
                execution_time_ms=execution_time_ms,
                memory_used_kb=memory_used_kb,
                provider_status=str(status_id),
                provider_token=token,
                error_type=error_type,
                error_message=compile_output or message or "Compilation failed",
            )

        if status == TestResultStatus.PASSED:
            # Optional local normalize check if expected_output present in response context
            return SingleExecutionResult(
                status=status,
                verdict=verdict,
                stdout=stdout,
                stderr=stderr,
                compile_output=compile_output,
                message=message,
                execution_time_ms=execution_time_ms,
                memory_used_kb=memory_used_kb,
                provider_status=str(status_id),
                provider_token=token,
            )

        return SingleExecutionResult(
            status=status,
            verdict=verdict,
            stdout=stdout,
            stderr=stderr,
            compile_output=compile_output,
            message=message,
            execution_time_ms=execution_time_ms,
            memory_used_kb=memory_used_kb,
            provider_status=str(status_id),
            provider_token=token,
            error_type=error_type,
            error_message=message or stderr or compile_output or error_type,
        )


def outputs_match(actual: str, expected: str) -> bool:
    return _normalize_output(actual) == _normalize_output(expected)

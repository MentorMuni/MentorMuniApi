"""CodeExecutionService — batch test execution via a provider adapter."""

from __future__ import annotations

import logging
from typing import Awaitable, Callable, Optional

from app.coding.enums import ExecutionStatus, TestResultStatus, Verdict
from app.coding.execution.judge0 import Judge0Provider, outputs_match
from app.coding.execution.types import (
    BatchExecutionReport,
    ExecuteRequest,
    SingleExecutionResult,
)

logger = logging.getLogger("coding.execution")

ProviderUpdateCallback = Callable[[str, Optional[str], Optional[str]], Awaitable[None]]


class CodeExecutionService:
    """Orchestrates multi-test execution via a provider adapter."""

    def __init__(self, provider: object | None = None) -> None:
        self.provider = provider or Judge0Provider()

    async def execute_batch(
        self,
        request: ExecuteRequest,
        *,
        on_provider_update: ProviderUpdateCallback | None = None,
    ) -> BatchExecutionReport:
        if not request.test_cases:
            return BatchExecutionReport(
                overall_verdict=Verdict.ACCEPTED,
                execution_status=ExecutionStatus.COMPLETED.value,
                passed_count=0,
                total_count=0,
                provider=self.provider.name,
                summary={"message": "no_tests"},
            )

        results: list[SingleExecutionResult] = []
        passed = 0
        max_time: int | None = None
        max_mem: int | None = None
        hard_fail_verdict: Verdict | None = None

        cpu_base = max(0.1, request.wall_timeout_ms / 1000.0)
        wall_base = max(1.0, (request.wall_timeout_ms / 1000.0) * 2)
        # Allow compile headroom in wall time
        wall_base = max(wall_base, request.compile_timeout_ms / 1000.0)

        for case in request.test_cases:
            cpu = case.cpu_time_limit_s or (cpu_base * request.language.time_multiplier)
            mem = case.memory_limit_kb or request.language.memory_limit_kb or request.default_memory_limit_kb
            one = await self.provider.execute_one(
                source_code=request.source_code,
                language_id=request.language.judge0_language_id,
                stdin=case.stdin,
                expected_output=case.expected_output,
                cpu_time_limit_s=cpu,
                wall_time_limit_s=wall_base,
                memory_limit_kb=int(mem),
                max_stdout_bytes=request.max_stdout_bytes,
                on_provider_update=on_provider_update,
            )

            # If provider returned Accepted but outputs diverge (edge), mark WA
            if (
                one.status == TestResultStatus.PASSED
                and case.expected_output is not None
                and not outputs_match(one.stdout, case.expected_output)
            ):
                one.status = TestResultStatus.FAILED
                one.verdict = Verdict.WRONG_ANSWER
                one.error_type = "wrong_answer"
                one.error_message = "Output mismatch"

            if one.status == TestResultStatus.PASSED:
                passed += 1
            elif one.verdict in (
                Verdict.COMPILATION_ERROR,
                Verdict.TIME_LIMIT_EXCEEDED,
                Verdict.MEMORY_LIMIT_EXCEEDED,
                Verdict.RUNTIME_ERROR,
            ):
                if hard_fail_verdict is None:
                    hard_fail_verdict = one.verdict

            if one.execution_time_ms is not None:
                max_time = one.execution_time_ms if max_time is None else max(max_time, one.execution_time_ms)
            if one.memory_used_kb is not None:
                max_mem = one.memory_used_kb if max_mem is None else max(max_mem, one.memory_used_kb)

            results.append(one)

            # Stop early on compilation error (remaining tests won't help)
            if one.verdict == Verdict.COMPILATION_ERROR:
                break

        total = len(request.test_cases)
        evaluated = len(results)
        if hard_fail_verdict == Verdict.COMPILATION_ERROR:
            overall = Verdict.COMPILATION_ERROR
        elif any(r.error_type == "provider_error" for r in results) and passed == 0:
            overall = Verdict.RUNTIME_ERROR if hard_fail_verdict else Verdict.RUNTIME_ERROR
            # Prefer system_error path via execution_status
            exec_status = ExecutionStatus.SYSTEM_ERROR.value
            return BatchExecutionReport(
                overall_verdict=hard_fail_verdict or Verdict.RUNTIME_ERROR,
                execution_status=exec_status,
                results=results,
                passed_count=passed,
                total_count=total,
                max_execution_time_ms=max_time,
                max_memory_used_kb=max_mem,
                provider=self.provider.name,
                summary={
                    "evaluated": evaluated,
                    "provider_failures": sum(1 for r in results if r.error_type == "provider_error"),
                },
            )
        elif passed == total and evaluated == total:
            overall = Verdict.ACCEPTED
        elif passed == 0:
            overall = hard_fail_verdict or Verdict.WRONG_ANSWER
        else:
            overall = Verdict.PARTIAL

        return BatchExecutionReport(
            overall_verdict=overall,
            execution_status=ExecutionStatus.COMPLETED.value,
            results=results,
            passed_count=passed,
            total_count=total,
            max_execution_time_ms=max_time,
            max_memory_used_kb=max_mem,
            provider=self.provider.name,
            summary={"evaluated": evaluated},
        )

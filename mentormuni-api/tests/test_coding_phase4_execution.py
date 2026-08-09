"""Unit tests for Phase 4 execution mapping and batch orchestration."""

from __future__ import annotations

import pytest

from app.coding import enums as coding_enums
from app.coding.execution import types as exec_types
from app.coding.execution.judge0 import Judge0Provider, outputs_match
from app.coding.execution.service import CodeExecutionService

# Avoid pytest collecting *Test* classes from domain modules
ExecutionStatus = coding_enums.ExecutionStatus
Verdict = coding_enums.Verdict
TRS = coding_enums.TestResultStatus
ExecuteRequest = exec_types.ExecuteRequest
LanguageConfig = exec_types.LanguageConfig
SingleExecutionResult = exec_types.SingleExecutionResult
CaseIn = exec_types.TestCaseInput


def test_outputs_match_normalizes_newlines() -> None:
    assert outputs_match("1 2\n", "1 2")
    assert outputs_match("1 2\r\n", "1 2")
    assert not outputs_match("1 2", "2 1")


def test_judge0_status_mapping_compilation_error() -> None:
    p = Judge0Provider(base_url="http://example.invalid", api_key="")
    mapped = p._map_result(
        {
            "stdout": None,
            "stderr": None,
            "compile_output": "error: expected ;",
            "message": None,
            "time": None,
            "memory": None,
        },
        6,
        "tok",
        1000,
    )
    assert mapped.verdict == Verdict.COMPILATION_ERROR
    assert mapped.status == TRS.ERROR


@pytest.mark.asyncio
async def test_batch_stops_on_compile_error() -> None:
    class FakeProvider:
        name = "fake"

        async def execute_one(self, **kwargs):  # noqa: ANN003
            return SingleExecutionResult(
                status=TRS.ERROR,
                verdict=Verdict.COMPILATION_ERROR,
                compile_output="boom",
                error_type="compilation_error",
            )

    svc = CodeExecutionService(provider=FakeProvider())  # type: ignore[arg-type]
    report = await svc.execute_batch(
        ExecuteRequest(
            source_code="bad",
            language=LanguageConfig(code="python", judge0_language_id=71),
            test_cases=[
                CaseIn(1, "a", "a"),
                CaseIn(2, "b", "b"),
            ],
            wall_timeout_ms=2000,
            compile_timeout_ms=5000,
            default_memory_limit_kb=128000,
            max_stdout_bytes=1000,
        )
    )
    assert report.overall_verdict == Verdict.COMPILATION_ERROR
    assert report.execution_status == ExecutionStatus.COMPLETED.value
    assert len(report.results) == 1  # early stop


@pytest.mark.asyncio
async def test_batch_partial_pass() -> None:
    class FakeProvider:
        name = "fake"
        n = 0

        async def execute_one(self, **kwargs):  # noqa: ANN003
            self.n += 1
            if self.n == 1:
                return SingleExecutionResult(
                    status=TRS.PASSED,
                    verdict=Verdict.ACCEPTED,
                    stdout="a",
                )
            return SingleExecutionResult(
                status=TRS.FAILED,
                verdict=Verdict.WRONG_ANSWER,
                stdout="no",
                error_type="wrong_answer",
            )

    svc = CodeExecutionService(provider=FakeProvider())  # type: ignore[arg-type]
    report = await svc.execute_batch(
        ExecuteRequest(
            source_code="x",
            language=LanguageConfig(code="python", judge0_language_id=71),
            test_cases=[
                CaseIn(1, "a", "a"),
                CaseIn(2, "b", "b"),
            ],
            wall_timeout_ms=2000,
            compile_timeout_ms=5000,
            default_memory_limit_kb=128000,
            max_stdout_bytes=1000,
        )
    )
    assert report.passed_count == 1
    assert report.total_count == 2
    assert report.overall_verdict == Verdict.PARTIAL

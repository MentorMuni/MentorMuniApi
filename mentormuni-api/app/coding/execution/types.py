"""Provider-agnostic execution types."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional

from app.coding.enums import TestResultStatus, Verdict


@dataclass(frozen=True)
class LanguageConfig:
    code: str
    judge0_language_id: int
    time_multiplier: float = 1.0
    memory_limit_kb: Optional[int] = None
    file_extension: str = ""


@dataclass(frozen=True)
class TestCaseInput:
    test_case_id: Optional[int]
    stdin: str
    expected_output: str
    weight: float = 1.0
    is_hidden: bool = False
    order_index: int = 0
    cpu_time_limit_s: Optional[float] = None
    memory_limit_kb: Optional[int] = None


@dataclass
class SingleExecutionResult:
    status: TestResultStatus
    verdict: Optional[Verdict]
    stdout: str = ""
    stderr: str = ""
    compile_output: str = ""
    message: str = ""
    execution_time_ms: Optional[int] = None
    memory_used_kb: Optional[int] = None
    provider_status: Optional[str] = None
    provider_token: Optional[str] = None
    error_type: Optional[str] = None
    error_message: Optional[str] = None


@dataclass
class BatchExecutionReport:
    overall_verdict: Verdict
    execution_status: str
    results: list[SingleExecutionResult] = field(default_factory=list)
    passed_count: int = 0
    total_count: int = 0
    max_execution_time_ms: Optional[int] = None
    max_memory_used_kb: Optional[int] = None
    provider: str = "judge0"
    summary: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ExecuteRequest:
    source_code: str
    language: LanguageConfig
    test_cases: list[TestCaseInput]
    wall_timeout_ms: int
    compile_timeout_ms: int
    default_memory_limit_kb: int
    max_stdout_bytes: int

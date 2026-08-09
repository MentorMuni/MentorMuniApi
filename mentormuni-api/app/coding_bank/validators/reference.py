"""Reference / test validation interfaces (no Judge0 coupling in MVP).

When CodeExecutionService is available, inject an executor that runs the
trusted reference solution against each candidate input and returns stdout.
Until then, ReferenceSolutionValidator can use a LocalPythonHarness (optional)
or mark execution checks as skipped — never invent pass/fail from the LLM.
"""

from __future__ import annotations

import ast
import asyncio
from dataclasses import dataclass
from typing import Optional, Protocol

from app.coding_bank.schemas import GeneratedProblemContract, GeneratedTestCase
from app.coding_bank.validators.types import CheckResult, ValidationReport


class ReferenceExecutor(Protocol):
    """Abstraction over future CodeExecutionService / local harness."""

    async def run_stdin(
        self,
        *,
        language: str,
        source_code: str,
        stdin: str,
        time_limit_ms: int = 2000,
        memory_limit_kb: int = 256000,
    ) -> "ExecutionProbe":
        ...


@dataclass
class ExecutionProbe:
    ok: bool
    stdout: str = ""
    stderr: str = ""
    error: str = ""


class NullReferenceExecutor:
    """Placeholder until Phase 4 execution is wired for bank validation."""

    async def run_stdin(
        self,
        *,
        language: str,
        source_code: str,
        stdin: str,
        time_limit_ms: int = 2000,
        memory_limit_kb: int = 256000,
    ) -> ExecutionProbe:
        return ExecutionProbe(ok=False, error="reference_executor_not_configured")


class LocalPythonAstGuard:
    """Static safety/shape checks on Python reference (deterministic, no exec)."""

    FORBIDDEN = ("os.system", "subprocess", "socket", "eval(", "exec(", "__import__")

    def check(self, source: str) -> list[str]:
        errors: list[str] = []
        for token in self.FORBIDDEN:
            if token in source:
                errors.append(f"forbidden construct in reference: {token}")
        try:
            ast.parse(source)
        except SyntaxError as e:
            errors.append(f"python reference syntax error: {e}")
        if "input(" not in source and "stdin" not in source and "sys.stdin" not in source:
            # Competitive style usually reads stdin; soft fail if clearly not I/O based
            if "print(" not in source:
                errors.append("python reference appears to lack I/O (input/print)")
        return errors


class ReferenceSolutionValidator:
    def __init__(self, executor: ReferenceExecutor | None = None) -> None:
        self.executor = executor or NullReferenceExecutor()
        self.ast_guard = LocalPythonAstGuard()

    async def validate(self, contract: GeneratedProblemContract) -> ValidationReport:
        report = ValidationReport(verdict="pass")
        py = next((r for r in contract.reference_solutions if r.language == "python"), None)
        if py is None:
            report.verdict = "fail"
            report.errors.append("missing python reference solution")
            report.checks.append(CheckResult("reference_present", False, "no python reference"))
            return report

        static_errs = self.ast_guard.check(py.code)
        report.checks.append(
            CheckResult(
                "reference_static",
                passed=not static_errs,
                message="ok" if not static_errs else "; ".join(static_errs[:3]),
            )
        )
        if static_errs:
            report.verdict = "fail"
            report.errors.extend(static_errs)
            return report

        # Probe executor availability with empty stdin — if not configured, skip runtime.
        probe = await self.executor.run_stdin(language="python", source_code=py.code, stdin="")
        if probe.error == "reference_executor_not_configured":
            report.checks.append(
                CheckResult(
                    "reference_runtime",
                    True,
                    "skipped — executor not configured; static checks only",
                    details={"skipped": True},
                )
            )
            return report

        # Executor available: light smoke (empty may fail; we only care compile-ish)
        report.checks.append(
            CheckResult(
                "reference_runtime_available",
                True,
                "executor configured; full test pass handled by TestCaseValidator",
            )
        )
        return report


class TestCaseValidator:
    """
    For each test input → run trusted reference → canonical expected output.
    Do NOT trust LLM expected_output when executor is available.
    Reject if reference fails any valid test.
    """

    REQUIRED_CATEGORY_HINTS = ("normal", "boundary")

    def __init__(self, executor: ReferenceExecutor | None = None) -> None:
        self.executor = executor or NullReferenceExecutor()

    def validate_categories(self, cases: list[GeneratedTestCase]) -> ValidationReport:
        report = ValidationReport(verdict="pass")
        cats = {c.category for c in cases}
        missing = [c for c in self.REQUIRED_CATEGORY_HINTS if c not in cats]
        extras_ok = len(cats) >= 3
        ok = not missing and extras_ok and len(cases) >= 5
        msg = "ok"
        if missing:
            msg = f"missing categories: {missing}"
        elif not extras_ok:
            msg = "need >= 3 distinct categories"
        elif len(cases) < 5:
            msg = "need >= 5 test cases"
        report.checks.append(CheckResult("test_categories", ok, msg, details={"categories": sorted(cats)}))
        if not ok:
            report.verdict = "fail"
            report.errors.append(msg)
        return report

    async def validate_against_reference(
        self, contract: GeneratedProblemContract
    ) -> ValidationReport:
        cat_report = self.validate_categories(contract.candidate_test_cases)
        if not cat_report.ok:
            return cat_report

        py = next((r for r in contract.reference_solutions if r.language == "python"), None)
        if py is None:
            return ValidationReport(verdict="fail", errors=["missing python reference"])

        # Detect executor
        probe = await self.executor.run_stdin(language="python", source_code=py.code, stdin="")
        if probe.error == "reference_executor_not_configured":
            # Without executor: reject blank LLM expected outputs; keep proposed otherwise
            # but mark as skipped for canonical rewrite.
            report = ValidationReport(verdict="pass")
            report.checks.append(
                CheckResult(
                    "test_execution",
                    True,
                    "skipped — executor not configured; LLM expected_output retained pending runtime",
                    details={"skipped": True},
                )
            )
            for i, case in enumerate(contract.candidate_test_cases):
                if case.expected_output is None or str(case.expected_output).strip() == "":
                    report.verdict = "fail"
                    report.errors.append(f"test[{i}] missing expected_output and no executor")
            if report.errors:
                report.checks.append(CheckResult("test_expected_present", False, "missing expected outputs"))
            return report

        report = ValidationReport(verdict="pass")
        canonical: dict[str, str] = {}
        for i, case in enumerate(contract.candidate_test_cases):
            result = await self.executor.run_stdin(
                language="python", source_code=py.code, stdin=case.input
            )
            if not result.ok:
                report.verdict = "fail"
                report.errors.append(
                    f"test[{i}] reference failed: {result.error or result.stderr[:200]}"
                )
                continue
            out = result.stdout.rstrip("\n")
            key = f"case_{i}"
            canonical[key] = out
            # If LLM provided expected and it differs, record but prefer canonical
            if case.expected_output is not None and case.expected_output.rstrip("\n") != out:
                report.checks.append(
                    CheckResult(
                        f"test_{i}_llm_mismatch",
                        True,
                        "LLM expected_output overwritten by reference stdout",
                        details={"llm": case.expected_output, "canonical": out},
                    )
                )
        report.canonical_outputs = canonical
        report.checks.append(
            CheckResult(
                "test_execution",
                report.verdict == "pass",
                "ok" if report.verdict == "pass" else "reference failed one or more tests",
                details={"executed": len(canonical)},
            )
        )
        return report

    def validate_sync_categories_only(self, contract: GeneratedProblemContract) -> ValidationReport:
        return self.validate_categories(contract.candidate_test_cases)


def run_async(coro):
    """Helper for sync call sites / tests."""
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(coro)
    raise RuntimeError("run_async called from running loop; await the coroutine instead")

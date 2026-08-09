"""Schema + deterministic content validators (no execution)."""

from __future__ import annotations

import re
from typing import Any

from pydantic import ValidationError

from app.coding_bank.schemas import GeneratedProblemContract
from app.coding_bank.validators.types import CheckResult, ValidationReport


class SchemaValidator:
    """Reject malformed LLM JSON via GeneratedProblemContract."""

    def validate(self, payload: Any) -> tuple[GeneratedProblemContract | None, ValidationReport]:
        report = ValidationReport(verdict="pass")
        try:
            if isinstance(payload, GeneratedProblemContract):
                contract = payload
            elif isinstance(payload, dict):
                contract = GeneratedProblemContract.model_validate(payload)
            else:
                raise TypeError(f"unsupported payload type: {type(payload)}")
            report.checks.append(CheckResult("schema", True, "contract valid"))
            return contract, report
        except (ValidationError, TypeError, ValueError) as e:
            report.verdict = "fail"
            report.errors.append(str(e))
            report.checks.append(CheckResult("schema", False, str(e)[:500]))
            return None, report


class ContentValidator:
    """Deterministic consistency checks on statement/examples/constraints."""

    _FORBIDDEN_MARKERS = (
        "leetcode.com",
        "hackerrank.com",
        "codesignal.com",
        "geeksforgeeks.org",
        "interviewbit.com",
    )

    def validate(self, contract: GeneratedProblemContract) -> ValidationReport:
        report = ValidationReport(verdict="pass")
        errors: list[str] = []

        text_blob = " ".join(
            [
                contract.title,
                contract.problem_statement,
                contract.explanation,
                contract.constraints,
            ]
        ).lower()
        for marker in self._FORBIDDEN_MARKERS:
            if marker in text_blob:
                errors.append(f"forbidden source marker: {marker}")

        if len(contract.problem_statement.strip()) < 80:
            errors.append("problem_statement too short / likely incomplete")

        if "input" not in contract.input_format.lower() and "first line" not in contract.input_format.lower():
            # soft signal only — still fail if format empty (schema already enforces min length)
            pass

        for i, ex in enumerate(contract.examples):
            if ex.input is None or ex.output is None:
                errors.append(f"example[{i}] missing input/output")
            if not str(ex.output).strip() and str(ex.input).strip():
                # empty output can be valid; only flag if both empty
                if not str(ex.input).strip():
                    errors.append(f"example[{i}] empty")

        # Constraints should mention at least one numeric bound when difficulty is not trivial-only
        if not re.search(r"\d", contract.constraints):
            errors.append("constraints lack numeric bounds")

        # Title / slug alignment soft check
        slug_words = set(contract.slug.split("-"))
        title_words = set(re.findall(r"[a-z0-9]+", contract.title.lower()))
        if slug_words and title_words and slug_words.isdisjoint(title_words):
            errors.append("slug and title appear unrelated")

        report.checks.append(
            CheckResult(
                "content",
                passed=not errors,
                message="ok" if not errors else "; ".join(errors[:5]),
                details={"error_count": len(errors)},
            )
        )
        if errors:
            report.verdict = "fail"
            report.errors.extend(errors)
        return report


class ComplexityValidator:
    """Checks complexity strings look coherent with difficulty (heuristic, deterministic)."""

    def validate(self, contract: GeneratedProblemContract) -> ValidationReport:
        report = ValidationReport(verdict="pass")
        errors: list[str] = []
        t = contract.expected_time_complexity.lower().replace(" ", "")
        if contract.difficulty == "easy" and ("o(n!)" in t or "o(2^n)" in t or "o(k^n)" in t):
            errors.append("easy difficulty incompatible with exponential expected time")
        if contract.difficulty == "hard" and t in {"o(1)", "o(logn)"}:
            errors.append("hard difficulty unlikely with trivial expected time")
        report.checks.append(
            CheckResult("complexity", passed=not errors, message="ok" if not errors else errors[0])
        )
        if errors:
            report.verdict = "fail"
            report.errors.extend(errors)
        return report

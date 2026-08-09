"""Validation result types for the coding question bank pipeline."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass
class CheckResult:
    name: str
    passed: bool
    message: str = ""
    details: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "passed": self.passed,
            "message": self.message,
            "details": self.details,
        }


@dataclass
class ValidationReport:
    verdict: str  # pass | fail | skipped
    quality_score: float = 0.0
    checks: list[CheckResult] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    duplicate_of_problem_id: Optional[int] = None
    # Canonical expected outputs recomputed from reference (input -> output)
    canonical_outputs: dict[str, str] = field(default_factory=dict)

    @property
    def ok(self) -> bool:
        return self.verdict == "pass"

    def to_dict(self) -> dict[str, Any]:
        return {
            "verdict": self.verdict,
            "quality_score": self.quality_score,
            "checks": [c.to_dict() for c in self.checks],
            "errors": self.errors,
            "duplicate_of_problem_id": self.duplicate_of_problem_id,
            "canonical_outputs": self.canonical_outputs,
        }

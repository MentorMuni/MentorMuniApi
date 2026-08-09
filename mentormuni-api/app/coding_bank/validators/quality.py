"""Heuristic quality scoring for review prioritization."""

from __future__ import annotations

from app.coding_bank.schemas import GeneratedProblemContract
from app.coding_bank.validators.types import CheckResult, ValidationReport


class QualityValidator:
    """
    Produces 0–100 quality_score. Does not alone approve/publish.
    Deterministic weights on coverage signals.
    """

    def score(self, contract: GeneratedProblemContract, prior: ValidationReport | None = None) -> ValidationReport:
        score = 40.0
        notes: list[str] = []

        # Examples
        if len(contract.examples) >= 2:
            score += 10
        if len(contract.examples) >= 3:
            score += 5

        # Tests / categories
        cats = {c.category for c in contract.candidate_test_cases}
        score += min(20.0, 4.0 * len(cats))
        hidden = sum(1 for c in contract.candidate_test_cases if c.is_hidden)
        public = len(contract.candidate_test_cases) - hidden
        if public >= 2 and hidden >= 3:
            score += 10
        else:
            notes.append("prefer >=2 public and >=3 hidden tests")

        # Languages
        if len(contract.supported_languages) >= 3:
            score += 5
        if len(contract.reference_solutions) >= 1:
            score += 5

        # Explanation richness
        if len(contract.explanation) >= 120:
            score += 5

        if prior and prior.ok:
            score += 5
        elif prior and not prior.ok:
            score = min(score, 40.0)
            notes.append("prior validation failed")

        score = max(0.0, min(100.0, score))
        report = ValidationReport(verdict="pass", quality_score=score)
        report.checks.append(
            CheckResult(
                "quality",
                True,
                f"score={score:.1f}",
                details={"notes": notes, "categories": sorted(cats)},
            )
        )
        return report

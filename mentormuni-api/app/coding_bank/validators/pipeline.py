"""ProblemValidator orchestration pipeline."""

from __future__ import annotations

from typing import Iterable, Optional

from app.coding_bank.schemas import GeneratedProblemContract
from app.coding_bank.validators.content import ComplexityValidator, ContentValidator, SchemaValidator
from app.coding_bank.validators.duplicate import DuplicateDetector, ExistingProblemRef
from app.coding_bank.validators.quality import QualityValidator
from app.coding_bank.validators.reference import ReferenceExecutor, ReferenceSolutionValidator, TestCaseValidator
from app.coding_bank.validators.types import ValidationReport


class ProblemValidator:
    """
    AI generation → schema → content → reference → tests → complexity → duplicate → quality.

    Deterministic wherever possible. Execution via injected ReferenceExecutor only.
    """

    def __init__(self, executor: ReferenceExecutor | None = None) -> None:
        self.schema = SchemaValidator()
        self.content = ContentValidator()
        self.complexity = ComplexityValidator()
        self.reference = ReferenceSolutionValidator(executor=executor)
        self.tests = TestCaseValidator(executor=executor)
        self.duplicates = DuplicateDetector()
        self.quality = QualityValidator()

    async def validate(
        self,
        payload: object,
        *,
        existing: Iterable[ExistingProblemRef] | None = None,
    ) -> tuple[Optional[GeneratedProblemContract], ValidationReport]:
        contract, schema_report = self.schema.validate(payload)
        if contract is None:
            schema_report.quality_score = 0.0
            return None, schema_report

        merged = ValidationReport(verdict="pass", checks=list(schema_report.checks))

        for step_name, step_report in [
            ("content", self.content.validate(contract)),
            ("complexity", self.complexity.validate(contract)),
        ]:
            merged.checks.extend(step_report.checks)
            if not step_report.ok:
                merged.verdict = "fail"
                merged.errors.extend(step_report.errors)

        ref_report = await self.reference.validate(contract)
        merged.checks.extend(ref_report.checks)
        if not ref_report.ok:
            merged.verdict = "fail"
            merged.errors.extend(ref_report.errors)

        test_report = await self.tests.validate_against_reference(contract)
        merged.checks.extend(test_report.checks)
        merged.canonical_outputs.update(test_report.canonical_outputs)
        if not test_report.ok:
            merged.verdict = "fail"
            merged.errors.extend(test_report.errors)

        dup_report = self.duplicates.validate(contract, existing or [])
        merged.checks.extend(dup_report.checks)
        if not dup_report.ok:
            merged.verdict = "fail"
            merged.errors.extend(dup_report.errors)
            merged.duplicate_of_problem_id = dup_report.duplicate_of_problem_id

        quality_report = self.quality.score(contract, prior=merged)
        merged.quality_score = quality_report.quality_score
        merged.checks.extend(quality_report.checks)
        if merged.verdict != "pass":
            # Cap quality when failed
            merged.quality_score = min(merged.quality_score, 40.0)

        return contract, merged

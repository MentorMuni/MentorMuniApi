"""Service façade for the coding question bank pipeline (admin/internal).

Does NOT auto-generate the 50-problem bank. Callers must explicitly invoke
generation after pipeline review.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.coding.enums import GenerationRunStatus, ProblemStatus
from app.coding.models import CodingGenerationRun, CodingProblem, CodingProblemVersion
from app.coding_bank import CURRICULUM_VERSION, PROMPT_VERSION
from app.coding_bank.curriculum import (
    CurriculumConfig,
    GenerationSpec,
    build_placement_curriculum_v1,
    curriculum_from_override,
)
from app.coding_bank.generator import CodingProblemGenerator, GenerationError
from app.coding_bank.promote import (
    apply_canonical_outputs,
    approve_problem,
    attach_relevance,
    mark_validating,
    mark_validation_outcome,
    persist_generated_problem,
    promote_to_published,
    record_validation,
    reject_problem,
)
from app.coding_bank.schemas import GeneratedProblemContract
from app.coding_bank.validators.duplicate import ExistingProblemRef
from app.coding_bank.validators.pipeline import ProblemValidator
from app.coding_bank.validators.reference import ReferenceExecutor


class CodingBankService:
    def __init__(
        self,
        db: Session,
        *,
        generator: CodingProblemGenerator | None = None,
        validator: ProblemValidator | None = None,
        executor: ReferenceExecutor | None = None,
    ) -> None:
        self.db = db
        self.generator = generator or CodingProblemGenerator()
        self.validator = validator or ProblemValidator(executor=executor)

    def default_curriculum(self) -> CurriculumConfig:
        return build_placement_curriculum_v1()

    def create_generation_run(
        self,
        *,
        curriculum: CurriculumConfig | None = None,
        model: str | None = None,
        created_by: str | None = None,
        config_override: dict[str, Any] | None = None,
    ) -> CodingGenerationRun:
        curriculum = curriculum or curriculum_from_override(config_override) or self.default_curriculum()
        run = CodingGenerationRun(
            status=GenerationRunStatus.PENDING.value,
            prompt_version=PROMPT_VERSION,
            model=model or self.generator.model,
            curriculum_version=curriculum.version,
            target_count=curriculum.target_count,
            generated_count=0,
            config_json=curriculum.to_dict(),
            created_by=created_by,
        )
        self.db.add(run)
        self.db.flush()
        return run

    def list_existing_refs(self) -> list[ExistingProblemRef]:
        rows = self.db.execute(
            select(
                CodingProblem.id,
                CodingProblem.topic,
                CodingProblem.pattern,
                CodingProblem.content_fingerprint,
                CodingProblemVersion.title,
                CodingProblemVersion.description,
                CodingProblemVersion.constraints_text,
            )
            .join(
                CodingProblemVersion,
                CodingProblemVersion.id == CodingProblem.current_version_id,
                isouter=True,
            )
            .where(CodingProblem.status != ProblemStatus.ARCHIVED.value)
        ).all()
        out: list[ExistingProblemRef] = []
        for r in rows:
            if r.title is None:
                continue
            out.append(
                ExistingProblemRef(
                    id=r.id,
                    title=r.title,
                    statement=r.description or "",
                    topic=r.topic,
                    pattern=r.pattern,
                    constraints=r.constraints_text,
                    fingerprint=r.content_fingerprint,
                )
            )
        return out

    async def ingest_and_validate(
        self,
        contract: GeneratedProblemContract,
        *,
        generation_run_id: int | None = None,
        prompt_version: str = PROMPT_VERSION,
        generation_model: str | None = None,
    ) -> tuple[CodingProblem, Any]:
        """Persist as GENERATED, run validation pipeline, move to pending_review or validation_failed."""
        problem, version = persist_generated_problem(
            self.db,
            contract,
            generation_run_id=generation_run_id,
            prompt_version=prompt_version,
            generation_model=generation_model,
            status=ProblemStatus.GENERATED.value,
        )
        mark_validating(self.db, problem)
        _c, report = await self.validator.validate(contract, existing=self.list_existing_refs())
        record_validation(self.db, problem, version, report, generation_run_id=generation_run_id)
        if report.ok and report.canonical_outputs:
            apply_canonical_outputs(self.db, version, report.canonical_outputs)
        mark_validation_outcome(self.db, problem, passed=report.ok)
        return problem, report

    async def generate_slot(
        self,
        run: CodingGenerationRun,
        spec: GenerationSpec,
    ) -> CodingProblem:
        """Generate one curriculum slot. Requires configured OpenAI client — not for auto-batch yet."""
        if run.status == GenerationRunStatus.PENDING.value:
            run.status = GenerationRunStatus.RUNNING.value
            run.started_at = datetime.now(timezone.utc)
        avoid_titles = [r.title for r in self.list_existing_refs()]
        avoid_slugs = [
            s for s in self.db.scalars(select(CodingProblem.slug)).all()
        ]
        try:
            contract = await self.generator.generate_one(
                spec, avoid_titles=avoid_titles, avoid_slugs=avoid_slugs
            )
        except GenerationError:
            run.last_error = f"slot {spec.slot_id} generation failed"
            raise
        problem, _report = await self.ingest_and_validate(
            contract,
            generation_run_id=run.id,
            prompt_version=run.prompt_version,
            generation_model=run.model,
        )
        run.generated_count = int(run.generated_count or 0) + 1
        self.db.flush()
        return problem

    def approve(self, problem_id: int, *, approved_by: str) -> CodingProblem:
        problem = self.db.get(CodingProblem, problem_id)
        if problem is None:
            raise ValueError("problem not found")
        return approve_problem(self.db, problem, approved_by=approved_by)

    def reject(self, problem_id: int, *, reason: str) -> CodingProblem:
        problem = self.db.get(CodingProblem, problem_id)
        if problem is None:
            raise ValueError("problem not found")
        return reject_problem(self.db, problem, reason=reason)

    def publish(self, problem_id: int) -> CodingProblem:
        problem = self.db.get(CodingProblem, problem_id)
        if problem is None:
            raise ValueError("problem not found")
        return promote_to_published(self.db, problem)

    def add_relevance(self, problem_id: int, **kwargs: Any) -> Any:
        return attach_relevance(self.db, problem_id, **kwargs)

    def complete_run(self, run: CodingGenerationRun, *, failed: bool = False) -> None:
        run.status = (
            GenerationRunStatus.FAILED.value if failed else GenerationRunStatus.SUCCEEDED.value
        )
        run.completed_at = datetime.now(timezone.utc)
        self.db.flush()

"""Persist generated contracts and promote approved problems into the production bank.

Uses existing CodingProblem / CodingProblemVersion tables — no duplicate production tables.
Never overwrites an immutable published version; publishing creates/points current_version.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.coding.enums import ProblemStatus, ValidationVerdict
from app.coding.models import (
    CodingProblem,
    CodingProblemVersion,
    CodingReferenceSolution,
    CodingTestCase,
    CodingValidationResult,
)
from app.coding_bank.lifecycle import LifecycleError, assert_transition, can_publish
from app.coding_bank.schemas import GeneratedProblemContract
from app.coding_bank.validators.duplicate import content_fingerprint
from app.coding_bank.validators.types import ValidationReport


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def persist_generated_problem(
    db: Session,
    contract: GeneratedProblemContract,
    *,
    generation_run_id: int | None = None,
    prompt_version: str,
    generation_model: str | None,
    status: str = ProblemStatus.GENERATED.value,
) -> tuple[CodingProblem, CodingProblemVersion]:
    """Create problem head + version v1 from a validated (or pre-validation) contract."""
    existing = db.scalar(select(CodingProblem).where(CodingProblem.slug == contract.slug))
    if existing is not None:
        raise LifecycleError(f"slug already exists: {contract.slug}")

    fp = content_fingerprint(
        contract.title, contract.problem_statement, contract.primary_topic(), contract.primary_pattern()
    )
    problem = CodingProblem(
        slug=contract.slug,
        status=status,
        difficulty=contract.difficulty,
        topic=contract.primary_topic(),
        pattern=contract.primary_pattern(),
        prompt_version=prompt_version,
        generation_model=generation_model,
        generation_run_id=generation_run_id,
        content_fingerprint=fp,
    )
    db.add(problem)
    db.flush()

    version = CodingProblemVersion(
        problem_id=problem.id,
        version_number=1,
        title=contract.title,
        description=contract.problem_statement,
        difficulty=contract.difficulty,
        topic=contract.primary_topic(),
        pattern=contract.primary_pattern(),
        constraints_text=contract.constraints,
        input_format=contract.input_format,
        output_format=contract.output_format,
        examples_json=[e.model_dump() for e in contract.examples],
        explanation_text=contract.explanation,
        expected_time_complexity=contract.expected_time_complexity,
        expected_space_complexity=contract.expected_space_complexity,
        concepts_json=list(contract.topics),
        starter_code_by_language=contract.starter_map(),
        supported_languages_json=list(contract.supported_languages),
        generation_payload_json=contract.to_persistence_dict(),
        weight_policy_json={"public_share": 0.2, "hidden_share": 0.8},
    )
    db.add(version)
    db.flush()

    for ref in contract.reference_solutions:
        db.add(
            CodingReferenceSolution(
                problem_version_id=version.id,
                language_code=ref.language,
                source_code=ref.code,
                notes=ref.notes,
            )
        )

    for i, tc in enumerate(contract.candidate_test_cases):
        expected = tc.expected_output if tc.expected_output is not None else ""
        db.add(
            CodingTestCase(
                problem_version_id=version.id,
                input=tc.input,
                expected_output=expected,
                is_hidden=tc.is_hidden,
                weight=tc.weight,
                order_index=tc.order_index if tc.order_index is not None else i,
                category=tc.category,
            )
        )

    problem.current_version_id = version.id
    db.flush()
    return problem, version


def apply_canonical_outputs(
    db: Session,
    version: CodingProblemVersion,
    canonical_outputs: dict[str, str],
) -> None:
    """Overwrite expected_output from reference execution results (case_0, case_1, ...)."""
    if not canonical_outputs:
        return
    cases = list(
        db.scalars(
            select(CodingTestCase)
            .where(CodingTestCase.problem_version_id == version.id)
            .order_by(CodingTestCase.order_index.asc(), CodingTestCase.id.asc())
        )
    )
    for i, case in enumerate(cases):
        key = f"case_{i}"
        if key in canonical_outputs:
            case.expected_output = canonical_outputs[key]
    db.flush()


def record_validation(
    db: Session,
    problem: CodingProblem,
    version: CodingProblemVersion | None,
    report: ValidationReport,
    *,
    generation_run_id: int | None = None,
) -> CodingValidationResult:
    row = CodingValidationResult(
        problem_id=problem.id,
        problem_version_id=version.id if version else None,
        generation_run_id=generation_run_id,
        verdict=ValidationVerdict.PASS.value if report.ok else ValidationVerdict.FAIL.value,
        quality_score=report.quality_score,
        checks_json={"checks": [c.to_dict() for c in report.checks]},
        errors_json=list(report.errors),
        duplicate_of_problem_id=report.duplicate_of_problem_id,
    )
    db.add(row)
    problem.quality_score = report.quality_score
    problem.validation_summary_json = report.to_dict()
    db.flush()
    return row


def mark_validating(db: Session, problem: CodingProblem) -> None:
    assert_transition(problem.status, ProblemStatus.VALIDATING)
    problem.status = ProblemStatus.VALIDATING.value
    db.flush()


def mark_validation_outcome(db: Session, problem: CodingProblem, passed: bool) -> None:
    target = ProblemStatus.PENDING_REVIEW if passed else ProblemStatus.VALIDATION_FAILED
    assert_transition(problem.status, target)
    problem.status = target.value
    db.flush()


def approve_problem(db: Session, problem: CodingProblem, *, approved_by: str) -> CodingProblem:
    assert_transition(problem.status, ProblemStatus.APPROVED)
    problem.status = ProblemStatus.APPROVED.value
    problem.approved_at = _utcnow()
    problem.approved_by = approved_by
    problem.rejected_reason = None
    db.flush()
    return problem


def reject_problem(db: Session, problem: CodingProblem, *, reason: str) -> CodingProblem:
    assert_transition(problem.status, ProblemStatus.REJECTED)
    problem.status = ProblemStatus.REJECTED.value
    problem.rejected_reason = reason
    db.flush()
    return problem


def promote_to_published(db: Session, problem: CodingProblem) -> CodingProblem:
    """
    Only APPROVED problems may be published into the student-facing bank.
    Does not mutate an already-published immutable version; sets status + published_at.
    Future content edits must create a new version_number under a new approval cycle.
    """
    if not can_publish(problem.status):
        raise LifecycleError(f"cannot publish from status={problem.status}")
    if problem.current_version_id is None:
        raise LifecycleError("cannot publish without current_version_id")

    assert_transition(problem.status, ProblemStatus.PUBLISHED)
    problem.status = ProblemStatus.PUBLISHED.value
    problem.published_at = _utcnow()
    db.flush()
    return problem


def create_new_draft_version_from_approved(
    db: Session,
    problem: CodingProblem,
    contract: GeneratedProblemContract,
) -> CodingProblemVersion:
    """
    For post-publish revisions: never overwrite published version rows.
    Creates version_number+1; leaves problem status as draft/generated until re-approved.
    Caller must move status off published first (archive + new slug) OR use a fork.
    This helper refuses if current status is published.
    """
    if problem.status == ProblemStatus.PUBLISHED.value:
        raise LifecycleError("refuse to mutate published problem; archive and create new slug, or fork")

    max_ver = db.scalar(
        select(CodingProblemVersion.version_number)
        .where(CodingProblemVersion.problem_id == problem.id)
        .order_by(CodingProblemVersion.version_number.desc())
        .limit(1)
    ) or 0
    version = CodingProblemVersion(
        problem_id=problem.id,
        version_number=int(max_ver) + 1,
        title=contract.title,
        description=contract.problem_statement,
        difficulty=contract.difficulty,
        topic=contract.primary_topic(),
        pattern=contract.primary_pattern(),
        constraints_text=contract.constraints,
        input_format=contract.input_format,
        output_format=contract.output_format,
        examples_json=[e.model_dump() for e in contract.examples],
        explanation_text=contract.explanation,
        expected_time_complexity=contract.expected_time_complexity,
        expected_space_complexity=contract.expected_space_complexity,
        concepts_json=list(contract.topics),
        starter_code_by_language=contract.starter_map(),
        supported_languages_json=list(contract.supported_languages),
        generation_payload_json=contract.to_persistence_dict(),
    )
    db.add(version)
    db.flush()
    problem.current_version_id = version.id
    return version


def attach_relevance(
    db: Session,
    problem_id: int,
    *,
    company_key: str,
    role_key: str = "software-engineer",
    round_key: str = "coding",
    relevance: str = "medium",
    company_name: str | None = None,
    role_name: str | None = None,
    evidence_confidence: float | None = None,
    evidence_notes: str | None = None,
    evidence_json: dict[str, Any] | None = None,
    source_metadata_json: dict[str, Any] | None = None,
) -> Any:
    from app.coding.models import CodingProblemRelevance

    row = CodingProblemRelevance(
        problem_id=problem_id,
        company_key=company_key,
        company_name=company_name,
        role_key=role_key,
        role_name=role_name,
        round_key=round_key,
        relevance=relevance,
        evidence_confidence=evidence_confidence,
        evidence_notes=evidence_notes,
        evidence_json=evidence_json,
        source_metadata_json=source_metadata_json,
    )
    db.add(row)
    db.flush()
    return row

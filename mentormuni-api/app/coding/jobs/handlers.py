"""Job handlers: run, submit_evaluate, analyze."""

from __future__ import annotations

import logging
from typing import Any

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.coding.analysis import CodingAnalysisService
from app.coding.enums import (
    AnalysisStatus,
    ExecutionStatus,
    JobType,
    TestResultStatus,
)
from app.services.coding_analysis_prompt import PROMPT_VERSION
from app.coding.execution.factory import get_code_execution_service
from app.coding.execution.types import ExecuteRequest, LanguageConfig, TestCaseInput
from app.coding.jobs import queue as job_queue
from app.coding.limits import get_coding_limits
from app.coding.models import (
    CodingAiAnalysis,
    CodingJob,
    CodingLanguage,
    CodingProblemVersion,
    CodingRun,
    CodingSubmission,
    CodingTestCase,
    CodingTestResult,
)
from app.coding.scoring import WeightedOutcome, score_from_test_outcomes

logger = logging.getLogger("coding.handlers")


def _public_result_summary(report_summary: dict[str, Any], results: list[Any]) -> dict[str, Any]:
    cases = []
    for i, r in enumerate(results):
        cases.append(
            {
                "index": i,
                "status": r.status.value if hasattr(r.status, "value") else str(r.status),
                "verdict": r.verdict.value if r.verdict and hasattr(r.verdict, "value") else (r.verdict or None),
                "execution_time_ms": r.execution_time_ms,
                "memory_used_kb": r.memory_used_kb,
                "error_type": r.error_type,
                "compile_output": (r.compile_output or "")[:500] or None,
                "stderr": (r.stderr or "")[:500] or None,
            }
        )
    return {"cases": cases, **(report_summary or {})}


async def handle_job(db: AsyncSession, job: CodingJob) -> None:
    await job_queue.mark_running(db, job)
    if job.job_type == JobType.RUN.value:
        await _handle_run(db, job)
        return
    if job.job_type == JobType.SUBMIT_EVALUATE.value:
        await _handle_submit_evaluate(db, job)
        return
    if job.job_type == JobType.ANALYZE.value:
        await _handle_analyze(db, job)
        return
    await job_queue.mark_failed(
        db, job, error=f"Unsupported job_type: {job.job_type}", retryable=False
    )


async def _load_language(db: AsyncSession, code: str) -> CodingLanguage | None:
    return (
        await db.execute(
            select(CodingLanguage).where(
                CodingLanguage.code == code,
                CodingLanguage.is_active.is_(True),
            )
        )
    ).scalar_one_or_none()


async def _execute_cases(
    db: AsyncSession,
    job: CodingJob,
    *,
    source: str,
    language: CodingLanguage,
    cases: list[CodingTestCase],
) -> Any:
    limits = get_coding_limits()
    request = ExecuteRequest(
        source_code=source,
        language=LanguageConfig(
            code=language.code,
            judge0_language_id=language.judge0_language_id,
            time_multiplier=float(language.time_multiplier or 1.0),
            memory_limit_kb=language.default_memory_limit_kb,
            file_extension=language.file_extension or "",
        ),
        test_cases=[
            TestCaseInput(
                test_case_id=tc.id,
                stdin=tc.input,
                expected_output=tc.expected_output,
                weight=float(tc.weight or 1.0),
                is_hidden=bool(tc.is_hidden),
                order_index=int(tc.order_index or 0),
            )
            for tc in cases
        ],
        wall_timeout_ms=limits.execution_timeout_ms,
        compile_timeout_ms=limits.compile_timeout_ms,
        default_memory_limit_kb=limits.memory_limit_kb,
        max_stdout_bytes=limits.max_stdout_bytes,
    )

    async def _on_provider(provider: str, token: str | None, status: str | None) -> None:
        await job_queue.update_provider_meta(
            db, job, provider=provider, token=token, provider_status=status
        )

    service = get_code_execution_service()
    return await service.execute_batch(request, on_provider_update=_on_provider)


async def _handle_run(db: AsyncSession, job: CodingJob) -> None:
    if not job.run_id:
        await job_queue.mark_failed(db, job, error="run job missing run_id", retryable=False)
        return
    run = (await db.execute(select(CodingRun).where(CodingRun.id == job.run_id))).scalar_one_or_none()
    if run is None:
        await job_queue.mark_failed(db, job, error="coding_run not found", retryable=False)
        return
    if run.execution_status == ExecutionStatus.COMPLETED.value and run.verdict:
        await job_queue.mark_succeeded(db, job)
        return

    run.execution_status = ExecutionStatus.RUNNING.value
    await db.flush()
    lang = await _load_language(db, run.language_code)
    if lang is None:
        run.execution_status = ExecutionStatus.SYSTEM_ERROR.value
        await db.flush()
        await job_queue.mark_failed(db, job, error="language not active", retryable=False)
        return

    cases = (
        await db.execute(
            select(CodingTestCase)
            .where(
                CodingTestCase.problem_version_id == run.problem_version_id,
                CodingTestCase.is_hidden.is_(False),
            )
            .order_by(CodingTestCase.order_index.asc(), CodingTestCase.id.asc())
        )
    ).scalars().all()

    try:
        report = await _execute_cases(
            db, job, source=run.source_code, language=lang, cases=list(cases)
        )
    except Exception as exc:  # noqa: BLE001
        logger.exception("coding_run_failed run_id=%s", run.id)
        run.execution_status = ExecutionStatus.SYSTEM_ERROR.value
        await db.flush()
        msg = f"{type(exc).__name__}: {exc}"
        non_retry = "JUDGE0" in msg.upper() or "not configured" in msg.lower() or "Unsupported coding" in msg
        await job_queue.mark_failed(db, job, error=msg, retryable=not non_retry)
        return

    run.passed_count = report.passed_count
    run.total_count = report.total_count
    run.execution_time_ms = report.max_execution_time_ms
    run.memory_used_kb = report.max_memory_used_kb
    run.verdict = report.overall_verdict.value if report.overall_verdict else None
    run.execution_status = report.execution_status
    run.result_summary_json = _public_result_summary(report.summary, report.results)
    await db.flush()
    if report.execution_status == ExecutionStatus.SYSTEM_ERROR.value:
        await job_queue.mark_failed(db, job, error="Execution provider failure", retryable=False)
        return
    await job_queue.mark_succeeded(db, job)


async def _handle_submit_evaluate(db: AsyncSession, job: CodingJob) -> None:
    if not job.submission_id:
        await job_queue.mark_failed(db, job, error="submit job missing submission_id", retryable=False)
        return
    sub = (
        await db.execute(select(CodingSubmission).where(CodingSubmission.id == job.submission_id))
    ).scalar_one_or_none()
    if sub is None:
        await job_queue.mark_failed(db, job, error="submission not found", retryable=False)
        return

    if sub.execution_status == ExecutionStatus.COMPLETED.value and sub.score is not None:
        # Idempotent — still ensure analyze job exists
        await job_queue.mark_succeeded(db, job)
        await _enqueue_analyze_if_needed(db, sub)
        return

    sub.execution_status = ExecutionStatus.RUNNING.value
    await db.flush()

    lang = await _load_language(db, sub.language_code)
    if lang is None:
        sub.execution_status = ExecutionStatus.SYSTEM_ERROR.value
        sub.analysis_status = AnalysisStatus.SKIPPED.value
        await db.flush()
        await job_queue.mark_failed(db, job, error="language not active", retryable=False)
        return

    cases = (
        await db.execute(
            select(CodingTestCase)
            .where(CodingTestCase.problem_version_id == sub.problem_version_id)
            .order_by(CodingTestCase.order_index.asc(), CodingTestCase.id.asc())
        )
    ).scalars().all()

    try:
        report = await _execute_cases(
            db, job, source=sub.source_code, language=lang, cases=list(cases)
        )
    except Exception as exc:  # noqa: BLE001
        logger.exception("coding_submit_failed submission_id=%s", sub.id)
        sub.execution_status = ExecutionStatus.SYSTEM_ERROR.value
        await db.flush()
        msg = f"{type(exc).__name__}: {exc}"
        non_retry = "JUDGE0" in msg.upper() or "not configured" in msg.lower() or "Unsupported coding" in msg
        await job_queue.mark_failed(db, job, error=msg, retryable=not non_retry)
        return

    # Replace prior results on retry (unique on submission_id + test_case_id)
    await db.execute(delete(CodingTestResult).where(CodingTestResult.submission_id == sub.id))

    # Persist per-test results (hide actual_output for hidden cases)
    for tc, result in zip(cases, report.results):
        status = (
            TestResultStatus.PASSED.value
            if result.status == TestResultStatus.PASSED
            else (
                TestResultStatus.ERROR.value
                if result.status == TestResultStatus.ERROR
                else TestResultStatus.FAILED.value
            )
        )
        db.add(
            CodingTestResult(
                submission_id=sub.id,
                test_case_id=tc.id,
                status=status,
                execution_time_ms=result.execution_time_ms,
                memory_used_kb=result.memory_used_kb,
                actual_output=(result.stdout or "")[:4000] if not tc.is_hidden else None,
                error_type=result.error_type,
                error_message=(result.error_message or "")[:2000] if result.error_message else None,
            )
        )

    outcomes = [
        WeightedOutcome(
            weight=float(tc.weight or 1.0),
            passed=(i < len(report.results) and report.results[i].status == TestResultStatus.PASSED),
        )
        for i, tc in enumerate(cases)
    ]
    # If compile failed early, remaining cases count as not passed
    while len(outcomes) < len(cases):
        outcomes.append(WeightedOutcome(weight=float(cases[len(outcomes)].weight or 1.0), passed=False))

    official = score_from_test_outcomes(outcomes)
    sub.score = official
    sub.verdict = report.overall_verdict.value if report.overall_verdict else None
    sub.execution_status = (
        ExecutionStatus.SYSTEM_ERROR.value
        if report.execution_status == ExecutionStatus.SYSTEM_ERROR.value
        else ExecutionStatus.COMPLETED.value
    )
    sub.execution_time_ms = report.max_execution_time_ms
    sub.memory_used_kb = report.max_memory_used_kb
    sub.analysis_status = AnalysisStatus.PENDING.value
    await db.flush()

    if sub.execution_status == ExecutionStatus.SYSTEM_ERROR.value:
        await job_queue.mark_failed(db, job, error="Execution provider failure", retryable=False)
        return

    await job_queue.mark_succeeded(db, job)
    await _enqueue_analyze_if_needed(db, sub)


async def _enqueue_analyze_if_needed(db: AsyncSession, sub: CodingSubmission) -> None:
    existing = (
        await db.execute(
            select(CodingJob.id).where(
                CodingJob.submission_id == sub.id,
                CodingJob.job_type == JobType.ANALYZE.value,
                CodingJob.status.in_(["pending", "claimed", "running", "succeeded"]),
            ).limit(1)
        )
    ).scalar_one_or_none()
    if existing:
        return
    await job_queue.enqueue_job(
        db,
        job_type=JobType.ANALYZE,
        student_id=sub.student_id,
        attempt_id=sub.attempt_id,
        submission_id=sub.id,
        payload={},
    )


async def _handle_analyze(db: AsyncSession, job: CodingJob) -> None:
    if not job.submission_id:
        await job_queue.mark_failed(db, job, error="analyze missing submission_id", retryable=False)
        return
    sub = (
        await db.execute(select(CodingSubmission).where(CodingSubmission.id == job.submission_id))
    ).scalar_one_or_none()
    if sub is None:
        await job_queue.mark_failed(db, job, error="submission not found", retryable=False)
        return

    existing = (
        await db.execute(
            select(CodingAiAnalysis).where(CodingAiAnalysis.submission_id == sub.id)
        )
    ).scalar_one_or_none()
    if existing:
        sub.analysis_status = AnalysisStatus.READY.value
        await db.flush()
        await job_queue.mark_succeeded(db, job)
        return

    if sub.execution_status != ExecutionStatus.COMPLETED.value:
        sub.analysis_status = AnalysisStatus.SKIPPED.value
        await db.flush()
        await job_queue.mark_succeeded(db, job)
        return

    version = (
        await db.execute(
            select(CodingProblemVersion).where(CodingProblemVersion.id == sub.problem_version_id)
        )
    ).scalar_one_or_none()
    if version is None:
        sub.analysis_status = AnalysisStatus.FAILED.value
        await db.flush()
        await job_queue.mark_failed(db, job, error="problem version missing", retryable=False)
        return

    results = (
        await db.execute(
            select(CodingTestResult).where(CodingTestResult.submission_id == sub.id)
        )
    ).scalars().all()
    failed_cats = sorted({(r.error_type or r.status) for r in results if r.status != "passed"})

    try:
        svc = CodingAnalysisService()
        payload = await svc.analyze(
            problem_title=version.title,
            problem_description=version.description,
            constraints=version.constraints_text or "",
            expected_complexity=f"{version.expected_time_complexity or '?'} / {version.expected_space_complexity or '?'}",
            expected_approach=version.expected_approach or "",
            language=sub.language_code,
            source_code=sub.source_code,
            passed=sum(1 for r in results if r.status == "passed"),
            total=len(results),
            official_score=float(sub.score or 0),
            verdict=sub.verdict or "",
            failed_categories=list(failed_cats),
            execution_metrics=f"time_ms={sub.execution_time_ms} memory_kb={sub.memory_used_kb}",
        )
    except Exception as exc:  # noqa: BLE001
        logger.warning("coding_analysis_failed submission_id=%s err=%s", sub.id, type(exc).__name__)
        sub.analysis_status = AnalysisStatus.FAILED.value
        await db.flush()
        # Analysis failure must not invalidate execution — mark job failed but non-critical retry once
        await job_queue.mark_failed(db, job, error=f"analysis: {type(exc).__name__}", retryable=True)
        return

    ca = payload.constraint_awareness
    db.add(
        CodingAiAnalysis(
            submission_id=sub.id,
            prompt_version=PROMPT_VERSION,
            model="gpt-4.1",
            overall_coaching_score=payload.overall_coaching_score,
            correctness_coaching_score=float(payload.correctness.get("score") or 0)
            if isinstance(payload.correctness, dict)
            else None,
            approach_score=float(payload.approach.get("score") or 0)
            if isinstance(payload.approach, dict)
            else None,
            complexity_score=float(payload.complexity.get("score") or 0)
            if isinstance(payload.complexity, dict)
            else None,
            code_quality_score=float(payload.code_quality.get("score") or 0)
            if isinstance(payload.code_quality, dict)
            else None,
            edge_case_score=float(payload.edge_cases.get("score") or 0)
            if isinstance(payload.edge_cases, dict)
            else None,
            understood_constraints=ca.understood_constraints,
            complexity_appropriate_for_constraints=ca.complexity_appropriate_for_constraints,
            missed_scalable_approach=ca.missed_scalable_approach,
            constraint_notes=ca.notes,
            detected_approach=str(payload.approach.get("detected") or "")
            if isinstance(payload.approach, dict)
            else None,
            time_complexity=str(payload.complexity.get("time") or "")
            if isinstance(payload.complexity, dict)
            else None,
            space_complexity=str(payload.complexity.get("space") or "")
            if isinstance(payload.complexity, dict)
            else None,
            analysis_json=payload.model_dump(),
            raw_response=None,
        )
    )
    sub.analysis_status = AnalysisStatus.READY.value
    await db.flush()
    await job_queue.mark_succeeded(db, job)

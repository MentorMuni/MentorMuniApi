"""Configurable coding limits — single place; no magic numbers in services."""

from __future__ import annotations

from dataclasses import dataclass

from app.core.config import settings


@dataclass(frozen=True)
class CodingLimits:
    max_source_bytes: int
    max_stdout_bytes: int
    run_rate_per_student: int
    run_rate_window_seconds: int
    submit_rate_per_student: int
    submit_rate_window_seconds: int
    execution_timeout_ms: int
    memory_limit_kb: int
    max_concurrent_jobs: int
    job_max_attempts: int
    job_poll_interval_ms: int
    compile_timeout_ms: int


def get_coding_limits() -> CodingLimits:
    return CodingLimits(
        max_source_bytes=settings.coding_max_source_bytes,
        max_stdout_bytes=settings.coding_max_stdout_bytes,
        run_rate_per_student=settings.coding_run_rate_per_student,
        run_rate_window_seconds=settings.coding_run_rate_window_seconds,
        submit_rate_per_student=settings.coding_submit_rate_per_student,
        submit_rate_window_seconds=settings.coding_submit_rate_window_seconds,
        execution_timeout_ms=settings.coding_execution_timeout_ms,
        memory_limit_kb=settings.coding_memory_limit_kb,
        max_concurrent_jobs=settings.coding_max_concurrent_jobs,
        job_max_attempts=settings.coding_job_max_attempts,
        job_poll_interval_ms=settings.coding_job_poll_interval_ms,
        compile_timeout_ms=settings.coding_compile_timeout_ms,
    )

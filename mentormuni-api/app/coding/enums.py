"""Coding domain status values (VARCHAR in Postgres, not native ENUM)."""

from __future__ import annotations

from enum import Enum


class ProblemStatus(str, Enum):
    """Lifecycle for coding_problems.status (student APIs only serve published)."""

    DRAFT = "draft"
    GENERATED = "generated"
    VALIDATING = "validating"
    VALIDATION_FAILED = "validation_failed"
    PENDING_REVIEW = "pending_review"
    APPROVED = "approved"
    REJECTED = "rejected"
    PUBLISHED = "published"
    ARCHIVED = "archived"


class GenerationRunStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ValidationVerdict(str, Enum):
    PASS = "pass"
    FAIL = "fail"
    SKIPPED = "skipped"


class RelevanceRound(str, Enum):
    CODING = "coding"
    ONLINE_ASSESSMENT = "online_assessment"
    TECHNICAL = "technical"
    UNKNOWN = "unknown"


class AssessmentStatus(str, Enum):
    DRAFT = "draft"
    ACTIVE = "active"
    ARCHIVED = "archived"


class AttemptStatus(str, Enum):
    IN_PROGRESS = "in_progress"
    SUBMITTED = "submitted"
    EXPIRED = "expired"


class ExecutionStatus(str, Enum):
    QUEUED = "queued"
    RUNNING = "running"
    EVALUATING = "evaluating"
    COMPLETED = "completed"
    SYSTEM_ERROR = "system_error"


class Verdict(str, Enum):
    ACCEPTED = "accepted"
    WRONG_ANSWER = "wrong_answer"
    PARTIAL = "partial"
    COMPILATION_ERROR = "compilation_error"
    RUNTIME_ERROR = "runtime_error"
    TIME_LIMIT_EXCEEDED = "time_limit_exceeded"
    MEMORY_LIMIT_EXCEEDED = "memory_limit_exceeded"


class AnalysisStatus(str, Enum):
    PENDING = "pending"
    READY = "ready"
    FAILED = "failed"
    SKIPPED = "skipped"


class JobType(str, Enum):
    RUN = "run"
    SUBMIT_EVALUATE = "submit_evaluate"
    ANALYZE = "analyze"


class JobStatus(str, Enum):
    PENDING = "pending"
    CLAIMED = "claimed"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    DEAD = "dead"


class TestResultStatus(str, Enum):
    PASSED = "passed"
    FAILED = "failed"
    ERROR = "error"
    SKIPPED = "skipped"

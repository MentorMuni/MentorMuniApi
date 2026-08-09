"""Lifecycle transitions for coding question bank problems.

GENERATED → VALIDATING → PENDING_REVIEW → APPROVED → PUBLISHED
                     ↘ VALIDATION_FAILED
              PENDING_REVIEW → REJECTED

Rejected / failed never become student-visible (students only see published).
"""

from __future__ import annotations

from app.coding.enums import ProblemStatus

ALLOWED_TRANSITIONS: dict[ProblemStatus, set[ProblemStatus]] = {
    ProblemStatus.DRAFT: {ProblemStatus.GENERATED, ProblemStatus.PENDING_REVIEW, ProblemStatus.ARCHIVED},
    ProblemStatus.GENERATED: {ProblemStatus.VALIDATING, ProblemStatus.ARCHIVED},
    ProblemStatus.VALIDATING: {
        ProblemStatus.VALIDATION_FAILED,
        ProblemStatus.PENDING_REVIEW,
        ProblemStatus.ARCHIVED,
    },
    ProblemStatus.VALIDATION_FAILED: {
        ProblemStatus.GENERATED,  # regenerate / retry
        ProblemStatus.VALIDATING,
        ProblemStatus.REJECTED,
        ProblemStatus.ARCHIVED,
    },
    ProblemStatus.PENDING_REVIEW: {
        ProblemStatus.APPROVED,
        ProblemStatus.REJECTED,
        ProblemStatus.VALIDATING,  # re-validate
        ProblemStatus.ARCHIVED,
    },
    ProblemStatus.APPROVED: {
        ProblemStatus.PUBLISHED,
        ProblemStatus.REJECTED,
        ProblemStatus.ARCHIVED,
    },
    ProblemStatus.REJECTED: {ProblemStatus.PENDING_REVIEW, ProblemStatus.ARCHIVED},
    ProblemStatus.PUBLISHED: {ProblemStatus.ARCHIVED},  # never overwrite published version content
    ProblemStatus.ARCHIVED: set(),
}


class LifecycleError(ValueError):
    pass


def assert_transition(current: str | ProblemStatus, target: str | ProblemStatus) -> None:
    cur = ProblemStatus(current) if not isinstance(current, ProblemStatus) else current
    tgt = ProblemStatus(target) if not isinstance(target, ProblemStatus) else target
    allowed = ALLOWED_TRANSITIONS.get(cur, set())
    if tgt not in allowed:
        raise LifecycleError(f"illegal transition {cur.value} → {tgt.value}")


def can_publish(status: str | ProblemStatus) -> bool:
    s = ProblemStatus(status) if not isinstance(status, ProblemStatus) else status
    return s == ProblemStatus.APPROVED

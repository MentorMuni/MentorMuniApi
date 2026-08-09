"""Duplicate / similarity detection for canonical problems."""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from difflib import SequenceMatcher
from typing import Iterable, Optional, Protocol

from app.coding_bank.schemas import GeneratedProblemContract
from app.coding_bank.validators.types import CheckResult, ValidationReport


def normalize_text(text: str) -> str:
    t = text.lower().strip()
    t = re.sub(r"\s+", " ", t)
    t = re.sub(r"[^a-z0-9\s]", "", t)
    return t


def content_fingerprint(title: str, statement: str, topic: str, pattern: str) -> str:
    blob = "|".join(
        [
            normalize_text(title),
            normalize_text(statement)[:2000],
            normalize_text(topic),
            normalize_text(pattern),
        ]
    )
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


@dataclass
class ExistingProblemRef:
    id: int
    title: str
    statement: str
    topic: str | None
    pattern: str | None
    constraints: str | None = None
    fingerprint: str | None = None
    embedding: list[float] | None = None  # reserved if embedding system exists


class EmbeddingSimilarity(Protocol):
    def cosine(self, a: list[float], b: list[float]) -> float:
        ...


class DuplicateDetector:
    """
    Compare normalized title, statement, topic, pattern, constraints.
    Optional embedding cosine if provided by an existing system.
    """

    def __init__(
        self,
        *,
        title_threshold: float = 0.92,
        statement_threshold: float = 0.86,
        embedding_threshold: float = 0.92,
        embedding: EmbeddingSimilarity | None = None,
    ) -> None:
        self.title_threshold = title_threshold
        self.statement_threshold = statement_threshold
        self.embedding_threshold = embedding_threshold
        self.embedding = embedding

    def similarity(self, a: str, b: str) -> float:
        return SequenceMatcher(None, normalize_text(a), normalize_text(b)).ratio()

    def find_duplicate(
        self,
        contract: GeneratedProblemContract,
        existing: Iterable[ExistingProblemRef],
    ) -> tuple[Optional[ExistingProblemRef], float, str]:
        best: Optional[ExistingProblemRef] = None
        best_score = 0.0
        best_reason = ""
        fp = content_fingerprint(
            contract.title, contract.problem_statement, contract.primary_topic(), contract.primary_pattern()
        )
        for ref in existing:
            if ref.fingerprint and ref.fingerprint == fp:
                return ref, 1.0, "exact_fingerprint"
            title_s = self.similarity(contract.title, ref.title)
            stmt_s = self.similarity(contract.problem_statement, ref.statement)
            topic_match = normalize_text(contract.primary_topic()) == normalize_text(ref.topic or "")
            pattern_match = normalize_text(contract.primary_pattern()) == normalize_text(ref.pattern or "")
            score = max(title_s, stmt_s)
            reason = "title" if title_s >= stmt_s else "statement"
            if topic_match and pattern_match and stmt_s >= self.statement_threshold * 0.95:
                score = max(score, stmt_s)
                reason = "topic_pattern_statement"
            if ref.constraints and contract.constraints:
                cons_s = self.similarity(contract.constraints, ref.constraints)
                if cons_s > 0.9 and stmt_s > 0.75:
                    score = max(score, 0.5 * cons_s + 0.5 * stmt_s)
                    reason = "constraints_statement"
            if (
                self.embedding
                and ref.embedding
                and getattr(contract, "_embedding", None)  # optional attach
            ):
                # Reserved path — unused unless caller attaches embeddings.
                pass
            if title_s >= self.title_threshold or stmt_s >= self.statement_threshold:
                if score > best_score:
                    best, best_score, best_reason = ref, score, reason
        return best, best_score, best_reason

    def validate(
        self,
        contract: GeneratedProblemContract,
        existing: Iterable[ExistingProblemRef],
    ) -> ValidationReport:
        report = ValidationReport(verdict="pass")
        dup, score, reason = self.find_duplicate(contract, existing)
        if dup is not None:
            report.verdict = "fail"
            report.duplicate_of_problem_id = dup.id
            report.errors.append(
                f"duplicate of problem_id={dup.id} score={score:.3f} reason={reason}"
            )
            report.checks.append(
                CheckResult(
                    "duplicate",
                    False,
                    report.errors[-1],
                    details={"problem_id": dup.id, "score": score, "reason": reason},
                )
            )
        else:
            report.checks.append(CheckResult("duplicate", True, "no near-duplicate found"))
        return report

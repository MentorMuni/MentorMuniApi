"""Bootstrap / seed published placement bank + per-topic practice assessments.

Usage (from mentormuni-api/):
  python -m app.coding_bank.bootstrap_seed
"""

from __future__ import annotations

import asyncio
import logging
import os
import sys

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.coding.models import CodingProblem, CodingProblemRelevance
from app.coding.practice import ensure_practice_assessment, normalize_topic_label
from app.coding_bank.seed_catalog import catalog_as_contracts as productish_catalog
from app.coding_bank.seed_catalog_service_v1 import catalog_as_contracts as service_catalog
from app.core.config import settings

logger = logging.getLogger("coding_bank.bootstrap")

# Pattern-theme relevance only — never claims an official company question.
SERVICE_COMPANY_RELEVANCE = [
    ("tcs", "TCS", "high", 0.72, "TCS NQT / Digital coding often emphasizes arrays, strings, matrices, basic sliding window."),
    ("infosys", "Infosys", "high", 0.7, "InfyTQ / SE tracks commonly test string manipulation, arrays, digit math, frequency counting."),
    ("accenture", "Accenture", "high", 0.68, "Accenture campus coding is typically easy–moderate array/string logic problems."),
    ("nagarro", "Nagarro", "medium", 0.62, "Nagarro OAs frequently stress hashing, strings, frequency, and basic array patterns."),
    ("persistent", "Persistent", "medium", 0.6, "Persistent campus coding commonly covers fundamentals + 1–2 easy coding tasks."),
    ("dassault", "Dassault Systèmes", "medium", 0.55, "Dassault campus screens include aptitude plus basic coding / string-logic style tasks."),
    ("impetus", "Impetus", "medium", 0.55, "Service-company campus style: fundamentals-first arrays/strings/math."),
]


def _async_db_url(url: str) -> str:
    if url.startswith("postgresql://"):
        return url.replace("postgresql://", "postgresql+asyncpg://", 1)
    if url.startswith("postgres://"):
        return url.replace("postgres://", "postgresql+asyncpg://", 1)
    return url


async def _refresh_contract(
    db: AsyncSession,
    problem: CodingProblem,
    contract,
) -> bool:
    """Update published problem content when seed catalog changes."""
    from sqlalchemy import delete

    from app.coding.models import (
        CodingProblemVersion,
        CodingReferenceSolution,
        CodingTestCase,
    )
    from app.coding_bank.validators.duplicate import content_fingerprint

    topic = normalize_topic_label(contract.primary_topic())
    problem.difficulty = contract.difficulty
    problem.topic = topic
    problem.pattern = contract.primary_pattern()
    problem.content_fingerprint = content_fingerprint(
        contract.title,
        contract.problem_statement,
        contract.primary_topic(),
        contract.primary_pattern(),
    )

    version = None
    if problem.current_version_id:
        version = await db.get(CodingProblemVersion, problem.current_version_id)
    if version is None:
        return False

    version.title = contract.title
    version.description = contract.problem_statement
    version.difficulty = contract.difficulty
    version.topic = topic
    version.pattern = contract.primary_pattern()
    version.constraints_text = contract.constraints
    version.input_format = contract.input_format
    version.output_format = contract.output_format
    version.examples_json = [e.model_dump() for e in contract.examples]
    version.explanation_text = contract.explanation
    version.expected_time_complexity = contract.expected_time_complexity
    version.expected_space_complexity = contract.expected_space_complexity
    version.concepts_json = list(contract.topics)
    version.starter_code_by_language = contract.starter_map()
    version.supported_languages_json = list(contract.supported_languages)
    version.generation_payload_json = contract.to_persistence_dict()

    await db.execute(
        delete(CodingReferenceSolution).where(
            CodingReferenceSolution.problem_version_id == version.id
        )
    )
    await db.execute(
        delete(CodingTestCase).where(CodingTestCase.problem_version_id == version.id)
    )
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
        db.add(
            CodingTestCase(
                problem_version_id=version.id,
                input=tc.input,
                expected_output=tc.expected_output or "",
                is_hidden=tc.is_hidden,
                weight=tc.weight,
                order_index=i,
                category=tc.category,
            )
        )
    await db.flush()
    return True


async def _persist_contract(
    db: AsyncSession,
    contract,
    *,
    generation_model: str,
    evidence_notes: str,
    evidence_confidence: float = 0.55,
) -> CodingProblem | None:
    from datetime import datetime, timezone

    from app.coding.enums import ProblemStatus
    from app.coding.models import (
        CodingProblemVersion,
        CodingReferenceSolution,
        CodingTestCase,
    )
    from app.coding_bank import PROMPT_VERSION
    from app.coding_bank.validators.duplicate import content_fingerprint

    existing = (
        await db.execute(select(CodingProblem).where(CodingProblem.slug == contract.slug))
    ).scalar_one_or_none()
    if existing is not None:
        refreshed = await _refresh_contract(db, existing, contract)
        if refreshed:
            logger.info("refreshed slug=%s", contract.slug)
        else:
            logger.info("skip existing slug=%s", contract.slug)
        return existing

    now = datetime.now(timezone.utc)
    topic = normalize_topic_label(contract.primary_topic())
    problem = CodingProblem(
        slug=contract.slug,
        status=ProblemStatus.PUBLISHED.value,
        difficulty=contract.difficulty,
        topic=topic,
        pattern=contract.primary_pattern(),
        role_key="software-engineer",
        role_name="Software Engineer / Campus Hire",
        prompt_version=PROMPT_VERSION,
        generation_model=generation_model,
        content_fingerprint=content_fingerprint(
            contract.title,
            contract.problem_statement,
            contract.primary_topic(),
            contract.primary_pattern(),
        ),
        approved_at=now,
        approved_by="bootstrap_seed",
        published_at=now,
        evidence_confidence=evidence_confidence,
        evidence_notes=evidence_notes,
    )
    db.add(problem)
    await db.flush()

    version = CodingProblemVersion(
        problem_id=problem.id,
        version_number=1,
        title=contract.title,
        description=contract.problem_statement,
        difficulty=contract.difficulty,
        topic=topic,
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
        time_limit_ms=2000,
        memory_limit_kb=256000,
    )
    db.add(version)
    await db.flush()

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
        db.add(
            CodingTestCase(
                problem_version_id=version.id,
                input=tc.input,
                expected_output=tc.expected_output or "",
                is_hidden=tc.is_hidden,
                weight=tc.weight,
                order_index=i,
                category=tc.category,
            )
        )
    problem.current_version_id = version.id
    await db.flush()
    return problem


async def _attach_service_relevance(db: AsyncSession, problem: CodingProblem) -> int:
    added = 0
    for company_key, company_name, relevance, conf, notes in SERVICE_COMPANY_RELEVANCE:
        exists = (
            await db.execute(
                select(CodingProblemRelevance.id).where(
                    CodingProblemRelevance.problem_id == problem.id,
                    CodingProblemRelevance.company_key == company_key,
                    CodingProblemRelevance.role_key == "software-engineer",
                    CodingProblemRelevance.round_key == "coding",
                )
            )
        ).scalar_one_or_none()
        if exists is not None:
            continue
        db.add(
            CodingProblemRelevance(
                problem_id=problem.id,
                company_key=company_key,
                company_name=company_name,
                role_key="software-engineer",
                role_name="Software Engineer / Campus Hire",
                round_key="coding",
                relevance=relevance,
                evidence_confidence=conf,
                evidence_notes=notes,
                source_metadata_json={
                    "source": "public_interview_experience_patterns",
                    "audience": "engineering_campus_placement_year4",
                    "disclaimer": "Theme alignment only — not an official company question.",
                },
            )
        )
        added += 1
    return added


async def seed_bank(db: AsyncSession) -> dict:
    batches = [
        (
            productish_catalog(),
            "seed_catalog_v1",
            "Curated placement bank (DSA patterns). Not an official company question.",
            0.5,
            False,
        ),
        (
            service_catalog(),
            "seed_catalog_service_v1",
            (
                "Service-company campus OA style (arrays/strings/math/frequency). "
                "Pattern-aligned for TCS/Infosys/Accenture/Nagarro/Persistent/Dassault/Impetus themes. "
                "Not an official company question."
            ),
            0.65,
            True,
        ),
    ]

    inserted = 0
    refreshed = 0
    relevance_rows = 0
    by_topic_diff: dict[tuple[str, str], list[CodingProblem]] = {}
    catalog_size = 0

    for contracts, model, notes, conf, attach_service in batches:
        catalog_size += len(contracts)
        for contract in contracts:
            before = (
                await db.execute(select(CodingProblem.id).where(CodingProblem.slug == contract.slug))
            ).scalar_one_or_none()
            problem = await _persist_contract(
                db,
                contract,
                generation_model=model,
                evidence_notes=notes,
                evidence_confidence=conf,
            )
            if problem is None:
                continue
            if before is None:
                inserted += 1
            else:
                refreshed += 1
            if attach_service:
                relevance_rows += await _attach_service_relevance(db, problem)
            key = (
                normalize_topic_label(problem.topic or ""),
                (problem.difficulty or "easy").lower(),
            )
            by_topic_diff.setdefault(key, []).append(problem)

    assessments = 0
    for (topic, difficulty), problems in by_topic_diff.items():
        if not topic:
            continue
        await ensure_practice_assessment(
            db,
            problems=problems[:5],
            topic=topic,
            difficulty=difficulty,
        )
        assessments += 1

    await db.commit()
    return {
        "problems_inserted": inserted,
        "problems_refreshed": refreshed,
        "problems_touched": sum(len(v) for v in by_topic_diff.values()),
        "topic_assessments": assessments,
        "catalog_size": catalog_size,
        "service_relevance_rows_added": relevance_rows,
    }


async def main() -> int:
    logging.basicConfig(level=logging.INFO)
    url = _async_db_url(settings.database_url or os.getenv("DATABASE_URL", ""))
    if not url:
        print("DATABASE_URL missing", file=sys.stderr)
        return 1
    engine = create_async_engine(url, pool_pre_ping=True)
    Session = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    async with Session() as db:
        result = await seed_bank(db)
        print(result)
    await engine.dispose()
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))

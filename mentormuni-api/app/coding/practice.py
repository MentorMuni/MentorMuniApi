"""Topic browser + practice resolve (bank-first, guarded generate on miss)."""

from __future__ import annotations

import hashlib
import logging
import re
from typing import Any, Optional

from fastapi import HTTPException
from openai import AsyncOpenAI
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.coding.access import ensure_student
from app.coding.browse_schemas import (
    BankProblemListOut,
    BankProblemOut,
    PracticeResolveOut,
    PracticeResolveRequest,
    TopicCatalogOut,
    TopicCountOut,
)
from app.coding.enums import AssessmentStatus, ProblemStatus
from app.coding.models import (
    CodingAssessment,
    CodingAssessmentProblem,
    CodingProblem,
    CodingProblemRelevance,
    CodingProblemVersion,
    CodingReferenceSolution,
    CodingTestCase,
)
from app.coding_bank import PROMPT_VERSION
from app.coding_bank.curriculum import GenerationSpec
from app.coding_bank.generator import CodingProblemGenerator, GenerationError
from app.coding_bank.schemas import GeneratedProblemContract
from app.coding_bank.validators.duplicate import ExistingProblemRef, content_fingerprint
from app.coding_bank.validators.pipeline import ProblemValidator
from app.core.config import settings
from app.models.user import User

logger = logging.getLogger("coding.practice")

# Canonical topic keys shown in the browser (placement curriculum).
CANONICAL_TOPICS: list[str] = [
    "Arrays",
    "Strings",
    "Hashing",
    "Math",
    "Two Pointers",
    "Sliding Window",
    "Binary Search",
    "Stack",
    "Queue",
    "Linked List",
    "Trees",
    "Graphs",
    "Greedy",
    "Recursion",
    "Backtracking",
    "Dynamic Programming",
]

_TOPIC_ALIASES: dict[str, str] = {
    "array": "Arrays",
    "arrays": "Arrays",
    "string": "Strings",
    "strings": "Strings",
    "hash": "Hashing",
    "hashing": "Hashing",
    "hashmap": "Hashing",
    "hash map": "Hashing",
    "math": "Math",
    "mathematics": "Math",
    "number theory": "Math",
    "two pointer": "Two Pointers",
    "two pointers": "Two Pointers",
    "sliding window": "Sliding Window",
    "binary search": "Binary Search",
    "stack": "Stack",
    "queue": "Queue",
    "linked list": "Linked List",
    "linkedlist": "Linked List",
    "tree": "Trees",
    "trees": "Trees",
    "bst": "Trees",
    "graph": "Graphs",
    "graphs": "Graphs",
    "greedy": "Greedy",
    "recursion": "Recursion",
    "backtracking": "Backtracking",
    "dp": "Dynamic Programming",
    "dynamic programming": "Dynamic Programming",
}


def normalize_difficulty(raw: str | None) -> str:
    key = (raw or "easy").strip().lower()
    if key in ("easy", "beginner", "basic"):
        return "easy"
    if key in ("medium", "intermediate", "moderate"):
        return "medium"
    if key in ("hard", "expert", "advanced"):
        return "hard"
    return "easy"


def normalize_topic_label(raw: str) -> str:
    key = re.sub(r"\s+", " ", (raw or "").strip().lower())
    if key in _TOPIC_ALIASES:
        return _TOPIC_ALIASES[key]
    for canon in CANONICAL_TOPICS:
        if canon.lower() == key:
            return canon
    # Title-case free text for display; keep student intent
    return (raw or "").strip().title()[:80] or "General"


def _slugify(text: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return s[:100] or "practice"


def _relevance_label(company_name: str | None) -> str | None:
    if company_name:
        return "Placement pattern practice"
    return "Campus coding-round practice"


def _why_matters(topic: str, pattern: str | None, company_name: str | None) -> str:
    base = f"Trains the {topic}"
    if pattern:
        base += f" / {pattern}"
    base += " pattern for campus placement coding rounds."
    if company_name:
        base += (
            f" Themed for {company_name}-style screens — evidence-based pattern practice, "
            "not an official company question."
        )
    return base


def _card_summary(description: str | None, *, limit: int = 180) -> str:
    text = re.sub(r"\s+", " ", (description or "").strip())
    if not text:
        return "Campus placement coding practice problem."
    if len(text) <= limit:
        return text
    cut = text[: limit - 1].rsplit(" ", 1)[0]
    return (cut or text[: limit - 1]).rstrip(".,;:") + "…"


def _bank_card(
    problem: CodingProblem,
    version: CodingProblemVersion,
    *,
    assessment_slug: str | None = None,
    company_name_override: str | None = None,
) -> BankProblemOut:
    topic = problem.topic or version.topic
    pattern = problem.pattern or version.pattern
    company = problem.company_name or company_name_override
    return BankProblemOut(
        id=problem.id,
        slug=problem.slug,
        title=version.title,
        difficulty=version.difficulty,
        topic=topic,
        pattern=pattern,
        summary=_card_summary(version.description),
        expected_time_complexity=version.expected_time_complexity,
        company_name=company,
        role_name=problem.role_name,
        relevance_label=_relevance_label(company),
        why_this_matters=_why_matters(topic or "DSA", pattern, company),
        assessment_slug=assessment_slug,
    )


async def list_topics(db: AsyncSession, user: User) -> TopicCatalogOut:
    ensure_student(user)
    rows = (
        await db.execute(
            select(
                CodingProblem.topic,
                CodingProblem.difficulty,
                CodingProblem.pattern,
                func.count(CodingProblem.id),
            )
            .where(CodingProblem.status == ProblemStatus.PUBLISHED.value)
            .where(CodingProblem.topic.is_not(None))
            .group_by(CodingProblem.topic, CodingProblem.difficulty, CodingProblem.pattern)
        )
    ).all()

    bucket: dict[str, dict[str, Any]] = {}
    for topic, difficulty, pattern, cnt in rows:
        t = (topic or "").strip()
        if not t:
            continue
        b = bucket.setdefault(t, {"count": 0, "diffs": set(), "patterns": set()})
        b["count"] += int(cnt or 0)
        if difficulty:
            b["diffs"].add(str(difficulty).lower())
        if pattern:
            b["patterns"].add(str(pattern))

    # Always surface curriculum topics even at zero so the browser feels complete.
    for canon in CANONICAL_TOPICS:
        bucket.setdefault(canon, {"count": 0, "diffs": set(), "patterns": set()})

    items = [
        TopicCountOut(
            topic=t,
            problem_count=int(data["count"]),
            difficulties=sorted(data["diffs"]),
            patterns=sorted(data["patterns"])[:12],
        )
        for t, data in sorted(bucket.items(), key=lambda kv: (-kv[1]["count"], kv[0].lower()))
    ]
    return TopicCatalogOut(items=items)


async def _first_assessment_slug_for_problem(db: AsyncSession, problem_id: int) -> str | None:
    row = (
        await db.execute(
            select(CodingAssessment.slug)
            .join(
                CodingAssessmentProblem,
                CodingAssessmentProblem.assessment_id == CodingAssessment.id,
            )
            .where(CodingAssessmentProblem.problem_id == problem_id)
            .where(CodingAssessment.status == AssessmentStatus.ACTIVE.value)
            .order_by(CodingAssessment.id.asc())
            .limit(1)
        )
    ).scalar_one_or_none()
    return row


async def list_bank_problems(
    db: AsyncSession,
    user: User,
    *,
    topic: str | None = None,
    difficulty: str | None = None,
    limit: int = 50,
) -> BankProblemListOut:
    ensure_student(user)
    q = (
        select(CodingProblem, CodingProblemVersion)
        .join(
            CodingProblemVersion,
            CodingProblemVersion.id == CodingProblem.current_version_id,
        )
        .where(CodingProblem.status == ProblemStatus.PUBLISHED.value)
    )
    topic_n = normalize_topic_label(topic) if topic else None
    diff_n = normalize_difficulty(difficulty) if difficulty else None
    if topic_n:
        q = q.where(func.lower(CodingProblem.topic) == topic_n.lower())
    if diff_n:
        q = q.where(func.lower(CodingProblem.difficulty) == diff_n)
    q = q.order_by(CodingProblem.topic.asc(), CodingProblem.difficulty.asc(), CodingProblem.id.asc()).limit(
        min(limit, 100)
    )
    rows = (await db.execute(q)).all()
    items: list[BankProblemOut] = []
    for problem, version in rows:
        assess_slug = await _first_assessment_slug_for_problem(db, problem.id)
        items.append(_bank_card(problem, version, assessment_slug=assess_slug))
    return BankProblemListOut(
        items=items,
        topic=topic_n,
        difficulty=diff_n,
        total=len(items),
    )


async def _existing_refs(db: AsyncSession) -> list[ExistingProblemRef]:
    rows = (
        await db.execute(
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
            .where(CodingProblem.status != "archived")
        )
    ).all()
    out: list[ExistingProblemRef] = []
    for r in rows:
        if not r.title:
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


async def _find_published(
    db: AsyncSession,
    *,
    topic: str,
    difficulty: str,
    limit: int,
) -> list[tuple[CodingProblem, CodingProblemVersion]]:
    q = (
        select(CodingProblem, CodingProblemVersion)
        .join(
            CodingProblemVersion,
            CodingProblemVersion.id == CodingProblem.current_version_id,
        )
        .where(CodingProblem.status == ProblemStatus.PUBLISHED.value)
        .where(func.lower(CodingProblem.topic) == topic.lower())
        .where(func.lower(CodingProblem.difficulty) == difficulty)
        .order_by(CodingProblem.id.asc())
        .limit(limit)
    )
    return list((await db.execute(q)).all())


async def ensure_practice_assessment(
    db: AsyncSession,
    *,
    problems: list[CodingProblem],
    topic: str,
    difficulty: str,
    company_key: str | None = None,
    company_name: str | None = None,
) -> CodingAssessment:
    """Create or reuse an active practice assessment wrapping these published problems."""
    if not problems:
        raise HTTPException(status_code=400, detail="No problems to attach.")
    slug_base = f"practice-{_slugify(topic)}-{difficulty}"
    if company_key:
        slug_base = f"{slug_base}-{_slugify(company_key)}"
    # Reuse if same slug exists and is active
    existing = (
        await db.execute(select(CodingAssessment).where(CodingAssessment.slug == slug_base))
    ).scalar_one_or_none()
    if existing is not None:
        # Ensure links exist
        for i, p in enumerate(problems):
            link = (
                await db.execute(
                    select(CodingAssessmentProblem).where(
                        CodingAssessmentProblem.assessment_id == existing.id,
                        CodingAssessmentProblem.problem_id == p.id,
                    )
                )
            ).scalar_one_or_none()
            if link is None:
                db.add(
                    CodingAssessmentProblem(
                        assessment_id=existing.id,
                        problem_id=p.id,
                        order_index=i,
                        points=100.0,
                    )
                )
        if company_key and not existing.company_key:
            existing.company_key = company_key
            existing.company_name = company_name
        await db.flush()
        return existing

    assessment = CodingAssessment(
        slug=slug_base,
        title=f"{topic} · {difficulty.title()} practice",
        company_key=company_key,
        company_name=company_name,
        role_key="software-engineer",
        role_name="Software Engineer / Campus Hire",
        difficulty=difficulty,
        duration_minutes=45 if difficulty != "hard" else 60,
        status=AssessmentStatus.ACTIVE.value,
        allowed_languages_json=["python", "cpp", "java"],
        evidence_confidence=0.55 if company_key else 0.4,
        evidence_json={
            "audience": "engineering_campus_placement_year4",
            "source": "topic_practice",
            "note": "Pattern practice — not an official company question.",
        },
    )
    db.add(assessment)
    await db.flush()
    for i, p in enumerate(problems):
        db.add(
            CodingAssessmentProblem(
                assessment_id=assessment.id,
                problem_id=p.id,
                order_index=i,
                points=100.0,
            )
        )
    await db.flush()
    return assessment


async def _persist_and_publish_generated(
    db: AsyncSession,
    contract: GeneratedProblemContract,
    *,
    company_key: str | None,
    company_name: str | None,
    model: str | None,
) -> CodingProblem:
    # Unique slug if collision
    slug = contract.slug
    clash = (
        await db.execute(select(CodingProblem.id).where(CodingProblem.slug == slug))
    ).scalar_one_or_none()
    if clash is not None:
        suffix = hashlib.sha1(contract.problem_statement.encode()).hexdigest()[:6]
        slug = f"{slug}-{suffix}"

    fp = content_fingerprint(
        contract.title, contract.problem_statement, contract.primary_topic(), contract.primary_pattern()
    )
    problem = CodingProblem(
        slug=slug,
        status=ProblemStatus.PUBLISHED.value,
        company_key=company_key,
        company_name=company_name,
        role_key="software-engineer",
        role_name="Software Engineer / Campus Hire",
        difficulty=contract.difficulty,
        topic=normalize_topic_label(contract.primary_topic()),
        pattern=contract.primary_pattern(),
        prompt_version=PROMPT_VERSION,
        generation_model=model,
        quality_score=None,
        content_fingerprint=fp,
        published_at=func.now(),  # type: ignore[arg-type]
        approved_at=func.now(),  # type: ignore[arg-type]
        approved_by="practice_resolve_auto",
        evidence_notes=(
            "Auto-promoted after validation for campus practice. "
            "Not an official company interview question."
        ),
        evidence_confidence=0.45,
    )
    # Fix timestamps — use Python utcnow instead of func in ORM assign
    from datetime import datetime, timezone

    now = datetime.now(timezone.utc)
    problem.published_at = now
    problem.approved_at = now

    db.add(problem)
    await db.flush()

    version = CodingProblemVersion(
        problem_id=problem.id,
        version_number=1,
        title=contract.title,
        description=contract.problem_statement,
        difficulty=contract.difficulty,
        topic=problem.topic,
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
                order_index=tc.order_index if tc.order_index is not None else i,
                category=tc.category,
            )
        )
    problem.current_version_id = version.id

    if company_key:
        db.add(
            CodingProblemRelevance(
                problem_id=problem.id,
                company_key=company_key,
                company_name=company_name,
                role_key="software-engineer",
                role_name="Software Engineer / Campus Hire",
                round_key="coding",
                relevance="medium",
                evidence_confidence=0.4,
                evidence_notes=(
                    "Theme alignment for campus coding rounds only — not a verified official question."
                ),
                source_metadata_json={"source": "practice_resolve", "audience": "year4_campus"},
            )
        )
    await db.flush()
    return problem


def _guess_pattern(topic: str) -> str:
    t = topic.lower()
    mapping = {
        "arrays": "traversal",
        "strings": "frequency",
        "hashing": "hash-map",
        "two pointers": "opposite-ends",
        "sliding window": "variable-window",
        "binary search": "classic",
        "stack": "monotonic-stack",
        "queue": "bfs-queue",
        "linked list": "two-pointers",
        "trees": "dfs",
        "graphs": "bfs",
        "greedy": "selection",
        "recursion": "divide-conquer",
        "backtracking": "subsets",
        "dynamic programming": "1d-dp",
    }
    return mapping.get(t, "fundamentals")


def _guess_complexity(difficulty: str) -> tuple[str, str]:
    if difficulty == "hard":
        return "O(n log n)", "O(n)"
    if difficulty == "medium":
        return "O(n)", "O(n)"
    return "O(n)", "O(1)"


async def resolve_practice(
    db: AsyncSession,
    user: User,
    body: PracticeResolveRequest,
) -> PracticeResolveOut:
    ensure_student(user)
    topic = normalize_topic_label(body.topic)
    difficulty = normalize_difficulty(body.difficulty)
    company_key = (body.company_key or "").strip().lower() or None
    company_name = (body.company_name or "").strip() or None
    if company_key and not company_name:
        company_name = company_key.replace("-", " ").title()

    matched = await _find_published(
        db, topic=topic, difficulty=difficulty, limit=body.max_problems
    )
    generated = False
    source = "bank"
    message = None

    if not matched:
        # Soft fallback: same topic, any difficulty
        soft = list(
            (
                await db.execute(
                    select(CodingProblem, CodingProblemVersion)
                    .join(
                        CodingProblemVersion,
                        CodingProblemVersion.id == CodingProblem.current_version_id,
                    )
                    .where(CodingProblem.status == ProblemStatus.PUBLISHED.value)
                    .where(func.lower(CodingProblem.topic) == topic.lower())
                    .order_by(CodingProblem.id.asc())
                    .limit(body.max_problems)
                )
            ).all()
        )
        if soft:
            matched = soft
            message = (
                f"No exact {difficulty} problems for {topic}; showing closest published set."
            )
            source = "bank"

    if not matched and body.allow_generate:
        if not settings.openai_api_key:
            raise HTTPException(
                status_code=503,
                detail=(
                    f"No published {topic} / {difficulty} problems yet, and generation is "
                    "unavailable (OPENAI_API_KEY missing)."
                ),
            )
        t_c, s_c = _guess_complexity(difficulty)
        pattern = _guess_pattern(topic)
        spec = GenerationSpec(
            slot_id=f"student-{_slugify(topic)}-{difficulty}",
            difficulty=difficulty,  # type: ignore[arg-type]
            topic=topic.lower(),
            pattern=pattern,
            expected_time_complexity=t_c,
            expected_space_complexity=s_c,
            notes=(
                "Audience: 4th-year engineering campus placement. "
                "Original wording only. Fair OA-style problem."
            ),
        )
        client = AsyncOpenAI(api_key=settings.openai_api_key)
        generator = CodingProblemGenerator(openai_client=client, model="gpt-4.1-mini")
        avoid_titles = [r.title for r in await _existing_refs(db)]
        avoid_slugs = list((await db.execute(select(CodingProblem.slug))).scalars().all())
        try:
            contract = await generator.generate_one(
                spec,
                avoid_titles=avoid_titles,
                avoid_slugs=avoid_slugs,
                company_name=company_name,
            )
        except GenerationError as e:
            logger.exception("practice generate failed")
            raise HTTPException(status_code=502, detail=f"Generation failed: {e}") from e

        validator = ProblemValidator()  # no Judge0 coupling
        _c, report = await validator.validate(contract, existing=await _existing_refs(db))
        if _c is None or not report.ok:
            raise HTTPException(
                status_code=422,
                detail={
                    "message": "Generated problem failed validation guardrails.",
                    "errors": report.errors[:8],
                },
            )
        # Apply canonical outputs if any (none without executor)
        problem = await _persist_and_publish_generated(
            db,
            contract,
            company_key=company_key,
            company_name=company_name,
            model=generator.model,
        )
        version = (
            await db.execute(
                select(CodingProblemVersion).where(
                    CodingProblemVersion.id == problem.current_version_id
                )
            )
        ).scalar_one()
        matched = [(problem, version)]
        generated = True
        source = "generated"
        message = (
            "Created an original campus-placement practice problem for your topic. "
            "Validated before publish — not an official company question."
        )

    if not matched:
        raise HTTPException(
            status_code=404,
            detail=(
                f"No practice available for topic '{topic}' at {difficulty}. "
                "Try a curriculum topic (Arrays, Hashing, DP, …) or enable generation."
            ),
        )

    problems = [p for p, _ in matched]
    assessment = await ensure_practice_assessment(
        db,
        problems=problems,
        topic=topic,
        difficulty=difficulty,
        company_key=company_key,
        company_name=company_name,
    )
    await db.commit()

    cards: list[BankProblemOut] = []
    for p, v in matched:
        cards.append(
            _bank_card(
                p,
                v,
                assessment_slug=assessment.slug,
                company_name_override=company_name,
            )
        )

    return PracticeResolveOut(
        source=source,
        assessment_id=assessment.id,
        assessment_slug=assessment.slug,
        title=assessment.title,
        topic=topic,
        difficulty=difficulty,
        problem_count=len(cards),
        generated=generated,
        message=message,
        problems=cards,
    )

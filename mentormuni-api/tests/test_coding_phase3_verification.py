"""Phase 3 final verification — eight production guarantees."""

from __future__ import annotations

import inspect
import uuid
from datetime import datetime, timedelta, timezone

import pytest
import pytest_asyncio
from fastapi import HTTPException
from sqlalchemy import select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import selectinload

from app.coding import service as coding_service
from app.coding.enums import AttemptStatus
from app.coding.models import (
    CodingAssessment,
    CodingAttempt,
    CodingAttemptSnapshot,
    CodingProblem,
    CodingProblemVersion,
    CodingReferenceSolution,
    CodingTestCase,
)
from app.coding.router import start_assessment as start_route
from app.coding.schemas import (
    AttemptOut,
    AttemptProblemOut,
    DraftOut,
    DraftUpsertRequest,
)
from app.coding.security_guards import ALWAYS_FORBIDDEN, assert_no_forbidden_keys
from app.common.security.passwords import hash_password
from app.models.enums import RoleCode, UserStatus
from app.models.organization import Organization
from app.models.role import Role
from app.models.user import User

pytestmark = pytest.mark.integration


def _normalize_url(url: str) -> str:
    if url.startswith("postgresql+asyncpg://"):
        return url
    if url.startswith("postgres://"):
        return "postgresql+asyncpg://" + url[len("postgres://") :]
    if url.startswith("postgresql://"):
        return "postgresql+asyncpg://" + url[len("postgresql://") :]
    return url


@pytest_asyncio.fixture(scope="module")
async def pg_ready(database_url: str | None) -> str:
    if not database_url:
        pytest.skip("DATABASE_URL / TEST_DATABASE_URL not set")
    engine = create_async_engine(_normalize_url(database_url), pool_pre_ping=True)
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
            exists = (
                await conn.execute(
                    text("SELECT to_regclass('public.coding_assessments') IS NOT NULL")
                )
            ).scalar()
            idx = (
                await conn.execute(
                    text(
                        "SELECT 1 FROM pg_indexes "
                        "WHERE indexname = 'uq_coding_attempts_active_student_assessment'"
                    )
                )
            ).scalar()
        if not exists:
            pytest.skip("coding tables missing — run alembic upgrade head")
        if not idx:
            pytest.skip("0018 unique index missing — run alembic upgrade head")
    except Exception:
        pytest.skip("PostgreSQL unreachable")
    finally:
        await engine.dispose()
    return database_url


@pytest_asyncio.fixture
async def db_session(pg_ready: str):
    engine = create_async_engine(_normalize_url(pg_ready), pool_pre_ping=True)
    factory = async_sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False, autoflush=False
    )
    async with factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
            await engine.dispose()


async def _student(session: AsyncSession, suffix: str) -> User:
    role = (
        await session.execute(select(Role).where(Role.role_code == RoleCode.STUDENT.value))
    ).scalar_one()
    org = (
        await session.execute(select(Organization).order_by(Organization.id.asc()).limit(1))
    ).scalar_one()
    email = f"p3-verify-{suffix}@test.local"
    existing = (
        await session.execute(
            select(User)
            .where(User.organization_id == org.id, User.email == email)
            .options(selectinload(User.role))
        )
    ).scalar_one_or_none()
    if existing:
        return existing
    user = User(
        organization_id=org.id,
        department_id=None,
        role_id=role.id,
        first_name="Verify",
        last_name=suffix,
        email=email,
        username=f"v_{suffix}"[:120],
        password_hash=hash_password("TestPass123!"),
        status=UserStatus.ACTIVE.value,
    )
    session.add(user)
    await session.flush()
    user.role = role
    return user


@pytest.mark.asyncio
async def test_verify_all_eight_guarantees(db_session: AsyncSession, pg_ready: str) -> None:
    user = await _student(db_session, uuid.uuid4().hex[:8])
    other = await _student(db_session, uuid.uuid4().hex[:8])

    assessment = (
        await db_session.execute(
            select(CodingAssessment).where(CodingAssessment.slug == "practice-two-sum")
        )
    ).scalar_one()
    # Restore seed catalog fields in case prior test runs mutated them
    assessment.title = "Practice Coding Round — Two Sum"
    assessment.duration_minutes = 45
    assessment.status = "active"
    problem_seed = (
        await db_session.execute(select(CodingProblem).where(CodingProblem.slug == "two-sum"))
    ).scalar_one()
    v1 = (
        await db_session.execute(
            select(CodingProblemVersion).where(
                CodingProblemVersion.problem_id == problem_seed.id,
                CodingProblemVersion.version_number == 1,
            )
        )
    ).scalar_one()
    problem_seed.current_version_id = v1.id
    await db_session.flush()

    # --- 4: ends_at is server-controlled (no client fields on start / draft) ---
    start_params = inspect.signature(start_route).parameters
    assert "body" not in start_params
    assert "ends_at" not in DraftUpsertRequest.model_fields

    attempt = await coding_service.start_assessment(db_session, user, "practice-two-sum")
    assert attempt.ends_at is not None
    assert attempt.seconds_remaining is not None
    # ends_at derived only from server clock + assessment duration at start
    expected_end = attempt.starts_at + timedelta(minutes=int(assessment.duration_minutes))
    delta = abs((attempt.ends_at - expected_end).total_seconds())
    assert delta < 5

    problem_id = attempt.problems[0].problem_id
    pinned_version_id = attempt.problems[0].problem_version_id

    # --- 1: cannot access problem not pinned to attempt ---
    with pytest.raises(HTTPException) as unpinned:
        await coding_service.get_attempt_problem(db_session, user, attempt.id, problem_id=9_999_999)
    assert unpinned.value.status_code == 404

    # --- 2: retrieval always uses pinned problem_version_id ---
    problem = (
        await db_session.execute(select(CodingProblem).where(CodingProblem.id == problem_id))
    ).scalar_one()
    live_before = problem.current_version_id
    assert live_before == pinned_version_id or live_before is not None

    max_vn = (
        await db_session.execute(
            select(CodingProblemVersion.version_number)
            .where(CodingProblemVersion.problem_id == problem.id)
            .order_by(CodingProblemVersion.version_number.desc())
            .limit(1)
        )
    ).scalar_one()
    mutated = CodingProblemVersion(
        problem_id=problem.id,
        version_number=int(max_vn) + 1,
        title="VERIFY_MUTATED_TITLE",
        description="must not appear on pinned attempt",
        difficulty="hard",
        examples_json=[],
        concepts_json=[],
        starter_code_by_language={"python": "# mutated"},
        weight_policy_json={},
    )
    db_session.add(mutated)
    await db_session.flush()
    problem.current_version_id = mutated.id
    assessment.title = "VERIFY_MUTATED_ASSESSMENT"
    assessment.duration_minutes = 999
    await db_session.flush()

    problem_out = await coding_service.get_attempt_problem(
        db_session, user, attempt.id, problem_id
    )
    assert problem_out.problem_version_id == pinned_version_id
    assert problem_out.title != "VERIFY_MUTATED_TITLE"
    assert problem_out.problem_version_id != mutated.id

    # --- 8: assessment/problem edits do not change snapshot ---
    snap = (
        await db_session.execute(
            select(CodingAttemptSnapshot).where(CodingAttemptSnapshot.attempt_id == attempt.id)
        )
    ).scalar_one()
    assert snap.snapshot_json["duration_minutes"] == 45
    assert "VERIFY_MUTATED" not in snap.snapshot_json["assessment_title"]
    frozen = await coding_service.get_attempt(db_session, user, attempt.id)
    assert frozen.assessment_title != "VERIFY_MUTATED_ASSESSMENT"
    assert frozen.problems[0].problem_version_id == pinned_version_id
    # ends_at unchanged despite duration_minutes=999
    assert frozen.ends_at == attempt.ends_at

    # --- 6: no hidden tests / reference / evidence / evaluator metadata ---
    for model in (AttemptOut, AttemptProblemOut, DraftOut):
        for key in ALWAYS_FORBIDDEN:
            assert key not in model.model_fields, f"{model.__name__} exposes {key}"

    payload = problem_out.model_dump()
    assert_no_forbidden_keys(payload)
    ref = (
        await db_session.execute(
            select(CodingReferenceSolution).where(
                CodingReferenceSolution.problem_version_id == pinned_version_id
            )
        )
    ).scalar_one()
    blob = str(payload)
    assert ref.source_code not in blob
    for tc in (
        await db_session.execute(
            select(CodingTestCase).where(
                CodingTestCase.problem_version_id == pinned_version_id,
                CodingTestCase.is_hidden.is_(True),
            )
        )
    ).scalars().all():
        # Full hidden stdin must never appear; outputs shared with public examples
        # are ambiguous — assert unique hidden outputs and all hidden inputs.
        assert tc.input not in blob
        if tc.expected_output.strip() not in {"1 2", "2 3"}:
            assert tc.expected_output not in blob
    assert "evidence_json" not in payload
    assert "evidence_notes" not in payload
    assert "evidence_confidence" not in payload
    # Explicit: no test-case collection fields
    assert "test_cases" not in payload
    assert "is_hidden" not in payload
    assert "reference_solution" not in payload
    assert "reference_solutions" not in payload

    list_out = await coding_service.list_assessments(db_session, user)
    assert_no_forbidden_keys(list_out.model_dump())
    assert_no_forbidden_keys(frozen.model_dump())

    # --- 5: cross-student attempt/draft denied ---
    with pytest.raises(HTTPException) as cross_a:
        await coding_service.get_attempt(db_session, other, attempt.id)
    assert cross_a.value.status_code == 404
    with pytest.raises(HTTPException) as cross_p:
        await coding_service.get_attempt_problem(db_session, other, attempt.id, problem_id)
    assert cross_p.value.status_code == 404

    await coding_service.upsert_draft(
        db_session,
        user,
        attempt.id,
        problem_id,
        DraftUpsertRequest(language_code="python", source_code="print(0)"),
    )
    with pytest.raises(HTTPException) as cross_d:
        await coding_service.get_draft(db_session, other, attempt.id, problem_id, "python")
    assert cross_d.value.status_code == 404
    with pytest.raises(HTTPException) as cross_du:
        await coding_service.upsert_draft(
            db_session,
            other,
            attempt.id,
            problem_id,
            DraftUpsertRequest(language_code="python", source_code="hack"),
        )
    assert cross_du.value.status_code == 404

    # --- 7: partial unique index blocks two simultaneous in_progress ---
    dup = CodingAttempt(
        student_id=user.id,
        assessment_id=assessment.id,
        status=AttemptStatus.IN_PROGRESS.value,
        starts_at=datetime.now(timezone.utc),
        ends_at=datetime.now(timezone.utc) + timedelta(minutes=10),
    )
    try:
        async with db_session.begin_nested():
            db_session.add(dup)
            await db_session.flush()
            raise AssertionError("expected unique index to reject second in_progress attempt")
    except IntegrityError:
        pass

    # --- 3: drafts blocked for expired / non-active ---
    attempt_row = (
        await db_session.execute(select(CodingAttempt).where(CodingAttempt.id == attempt.id))
    ).scalar_one()
    attempt_row.ends_at = datetime.now(timezone.utc) - timedelta(seconds=2)
    await db_session.flush()
    with pytest.raises(HTTPException) as expired_draft:
        await coding_service.upsert_draft(
            db_session,
            user,
            attempt_row.id,
            problem_id,
            DraftUpsertRequest(language_code="python", source_code="late"),
        )
    assert expired_draft.value.status_code == 409

    attempt_row.status = AttemptStatus.SUBMITTED.value
    attempt_row.ends_at = datetime.now(timezone.utc) + timedelta(minutes=30)
    await db_session.flush()
    with pytest.raises(HTTPException) as submitted_draft:
        await coding_service.upsert_draft(
            db_session,
            user,
            attempt_row.id,
            problem_id,
            DraftUpsertRequest(language_code="python", source_code="nope"),
        )
    assert submitted_draft.value.status_code == 409

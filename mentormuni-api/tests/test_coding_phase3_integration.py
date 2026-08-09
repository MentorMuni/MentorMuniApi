"""Integration tests for coding Phase 3 (PostgreSQL required)."""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

import pytest
import pytest_asyncio
from fastapi import HTTPException
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import selectinload

from app.coding import service as coding_service
from app.coding.enums import AssessmentStatus, AttemptStatus
from app.coding.models import (
    CodingAssessment,
    CodingAttempt,
    CodingAttemptSnapshot,
    CodingProblem,
    CodingProblemVersion,
    CodingReferenceSolution,
    CodingTestCase,
)
from app.coding.schemas import DraftUpsertRequest
from app.coding.security_guards import assert_no_forbidden_keys
from app.common.security.passwords import hash_password
from app.main import app
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


async def _db_reachable(url: str) -> bool:
    engine = create_async_engine(_normalize_url(url), pool_pre_ping=True)
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        return True
    except Exception:
        return False
    finally:
        await engine.dispose()


@pytest_asyncio.fixture(scope="module")
async def pg_ready(database_url: str | None) -> str:
    if not database_url:
        pytest.skip("DATABASE_URL / TEST_DATABASE_URL not set — skipping integration tests")
    if not await _db_reachable(database_url):
        pytest.skip(
            "PostgreSQL unreachable — skipping integration tests "
            "(do not claim migration verification)"
        )
    engine = create_async_engine(_normalize_url(database_url), pool_pre_ping=True)
    try:
        async with engine.connect() as conn:
            exists = (
                await conn.execute(
                    text("SELECT to_regclass('public.coding_assessments') IS NOT NULL")
                )
            ).scalar()
        if not exists:
            pytest.skip("coding_* tables missing — run: alembic upgrade head")
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
    ).scalar_one_or_none()
    if role is None:
        pytest.skip("STUDENT role not seeded")
    org = (
        await session.execute(select(Organization).order_by(Organization.id.asc()).limit(1))
    ).scalar_one_or_none()
    if org is None:
        pytest.skip("No organization available")

    email = f"coding-phase3-{suffix}@test.local"
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
        first_name="Coding",
        last_name=suffix,
        email=email,
        username=f"c_{suffix}"[:120],
        password_hash=hash_password("TestPass123!"),
        status=UserStatus.ACTIVE.value,
    )
    session.add(user)
    await session.flush()
    user.role = role
    return user


@pytest.mark.asyncio
async def test_http_unauthenticated_rejected(pg_ready: str) -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/api/coding/assessments")
    assert resp.status_code in (401, 403)


@pytest.mark.asyncio
async def test_phase3_lifecycle_snapshot_draft_authz(db_session: AsyncSession, pg_ready: str) -> None:
    user = await _student(db_session, uuid.uuid4().hex[:8])
    other = await _student(db_session, uuid.uuid4().hex[:8])

    assessment = (
        await db_session.execute(
            select(CodingAssessment).where(CodingAssessment.slug == "practice-two-sum")
        )
    ).scalar_one_or_none()
    if assessment is None:
        pytest.skip("Seed assessment practice-two-sum missing")

    # Restore active if a previous test left it draft
    assessment.status = AssessmentStatus.ACTIVE.value
    await db_session.flush()

    a1 = await coding_service.start_assessment(db_session, user, "practice-two-sum")
    a2 = await coding_service.start_assessment(db_session, user, assessment.id)
    assert a1.id == a2.id
    assert a1.status == AttemptStatus.IN_PROGRESS.value

    problem_id = a1.problems[0].problem_id
    version_id = a1.problems[0].problem_version_id
    original_title = a1.problems[0].title

    # Mutate live catalog — must not affect frozen attempt
    assessment.title = "MUTATED TITLE"
    assessment.duration_minutes = 999
    problem = (
        await db_session.execute(select(CodingProblem).where(CodingProblem.id == problem_id))
    ).scalar_one()
    max_vn = (
        await db_session.execute(
            select(CodingProblemVersion.version_number)
            .where(CodingProblemVersion.problem_id == problem.id)
            .order_by(CodingProblemVersion.version_number.desc())
            .limit(1)
        )
    ).scalar_one()
    new_ver = CodingProblemVersion(
        problem_id=problem.id,
        version_number=int(max_vn) + 1,
        title="MUTATED PROBLEM",
        description="should not appear",
        difficulty="hard",
        examples_json=[],
        concepts_json=[],
        starter_code_by_language={"python": "# mutated"},
        weight_policy_json={},
    )
    db_session.add(new_ver)
    await db_session.flush()
    problem.current_version_id = new_ver.id
    await db_session.flush()

    frozen = await coding_service.get_attempt(db_session, user, a1.id)
    assert frozen.assessment_title != "MUTATED TITLE"
    assert frozen.problems[0].problem_version_id == version_id
    assert frozen.problems[0].title == original_title

    snap = (
        await db_session.execute(
            select(CodingAttemptSnapshot).where(CodingAttemptSnapshot.attempt_id == a1.id)
        )
    ).scalar_one()
    assert snap.snapshot_json["duration_minutes"] == 45
    assert "MUTATED" not in snap.snapshot_json["assessment_title"]

    problem_out = await coding_service.get_attempt_problem(
        db_session, user, a1.id, problem_id
    )
    assert problem_out.problem_version_id == version_id
    assert problem_out.title == original_title
    payload = problem_out.model_dump()
    assert_no_forbidden_keys(payload)

    ref = (
        await db_session.execute(
            select(CodingReferenceSolution).where(
                CodingReferenceSolution.problem_version_id == version_id
            )
        )
    ).scalar_one()
    blob = str(payload)
    assert ref.source_code not in blob

    for tc in (
        await db_session.execute(
            select(CodingTestCase).where(
                CodingTestCase.problem_version_id == version_id,
                CodingTestCase.is_hidden.is_(True),
            )
        )
    ).scalars().all():
        assert tc.input not in blob
        assert tc.expected_output not in blob

    d1 = await coding_service.upsert_draft(
        db_session,
        user,
        a1.id,
        problem_id,
        DraftUpsertRequest(language_code="python", source_code="print(1)"),
    )
    d2 = await coding_service.upsert_draft(
        db_session,
        user,
        a1.id,
        problem_id,
        DraftUpsertRequest(language_code="python", source_code="print(2)"),
    )
    assert d1.id == d2.id
    got = await coding_service.get_draft(db_session, user, a1.id, problem_id, "python")
    assert got.source_code == "print(2)"
    assert_no_forbidden_keys(got.model_dump(), allow_draft_source=True)

    with pytest.raises(HTTPException) as e1:
        await coding_service.get_attempt(db_session, other, a1.id)
    assert e1.value.status_code == 404

    with pytest.raises(HTTPException) as e2:
        await coding_service.get_draft(db_session, other, a1.id, problem_id, "python")
    assert e2.value.status_code == 404

    assessment.status = AssessmentStatus.DRAFT.value
    await db_session.flush()
    with pytest.raises(HTTPException) as e3:
        await coding_service.start_assessment(db_session, user, "practice-two-sum")
    assert e3.value.status_code == 404
    assessment.status = AssessmentStatus.ACTIVE.value
    await db_session.flush()

    # Cross-org: create assessment owned by another org id if possible
    orgs = (await db_session.execute(select(Organization).order_by(Organization.id))).scalars().all()
    if len(orgs) >= 2 and user.organization_id != orgs[1].id:
        foreign = CodingAssessment(
            slug=f"foreign-{uuid.uuid4().hex[:8]}",
            title="Foreign",
            organization_id=orgs[1].id,
            duration_minutes=30,
            status=AssessmentStatus.ACTIVE.value,
            allowed_languages_json=["python"],
        )
        db_session.add(foreign)
        await db_session.flush()
        with pytest.raises(HTTPException) as e4:
            await coding_service.start_assessment(db_session, user, foreign.slug)
        assert e4.value.status_code in (403, 404)

    attempt_row = (
        await db_session.execute(select(CodingAttempt).where(CodingAttempt.id == a1.id))
    ).scalar_one()
    attempt_row.ends_at = datetime.now(timezone.utc) - timedelta(seconds=2)
    await db_session.flush()
    with pytest.raises(HTTPException) as e5:
        await coding_service.upsert_draft(
            db_session,
            user,
            a1.id,
            problem_id,
            DraftUpsertRequest(language_code="python", source_code="x"),
        )
    assert e5.value.status_code == 409

    expired_view = await coding_service.get_attempt(db_session, user, a1.id)
    assert expired_view.status == AttemptStatus.EXPIRED.value
    assert expired_view.is_expired is True

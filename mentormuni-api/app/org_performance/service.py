"""Aggregate student roadmap scores for TPO/HOD performance dashboards."""

from __future__ import annotations

import logging
from collections import Counter, defaultdict
from datetime import date, datetime, timezone
from typing import Any, Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.common.tenant.context import TenantContext
from app.models.department import Department
from app.models.enums import RoleCode, UserStatus
from app.models.role import Role
from app.models.upcoming_drive import UpcomingDrive
from app.models.user import User
from app.org_performance.schemas import (
    AreaBoard,
    AreaLeader,
    ClarityBoard,
    DeptPerformanceRow,
    GapStrengthItem,
    LeaderboardEntry,
    LevelFunnelItem,
    PerformanceBands,
    PerformanceSummaryOut,
    PillarAverages,
    RankedStudent,
    ScorecardListOut,
    StudentScorecard,
    TestsAggregate,
    ToolCoverageItem,
)
from app.student_roadmap.constants import (
    STEP_STATUS_CURRENT,
    STEP_STATUS_DONE,
    STEP_STATUS_LOCKED,
    TOOL_META,
    WEEK1_NUMBER,
    WEEK1_STEPS,
)
from app.student_roadmap.models import StudentAssessmentResult, StudentRoadmapStep, StudentRoadmapWeek

logger = logging.getLogger(__name__)

PILLAR_TOOLS: dict[str, tuple[str, ...]] = {
    "snap": ("5_sec",),
    "aptitude": ("aptitude",),
    # coding comes from coding_submissions (merged into scores_by_tool as "coding")
    "skills": ("skill_readiness", "skill_mock", "coding"),
    "interview": ("interview_readiness", "interview_mock", "project_mock", "hr_mock"),
}
MOCK_TOOLS = frozenset({"skill_mock", "project_mock", "interview_mock", "hr_mock"})
TOOLS_TOTAL = len(WEEK1_STEPS)

AREA_META: dict[str, dict[str, str]] = {
    "overall": {
        "label": "Overall readiness",
        "description": "Composite of completed baseline tool scores — primary ranking",
    },
    "aptitude": {
        "label": "Aptitude",
        "description": "Quantitative / logical aptitude readiness",
    },
    "skills": {
        "label": "Skills / coding",
        "description": "Skill readiness, skill AI mock, and coding assessment best score",
    },
    "coding": {
        "label": "Coding assessments",
        "description": "Best official coding submission score (Judge0 / local runner)",
    },
    "interview": {
        "label": "Interview / mocks",
        "description": "Interview readiness and AI mock rounds",
    },
    "communication": {
        "label": "Communication",
        "description": "Communication scores from completed assessments",
    },
    "technical": {
        "label": "Technical depth",
        "description": "Technical scores from completed assessments",
    },
    "shortlist": {
        "label": "Placement shortlist",
        "description": "Composite of readiness + communication + technical + coding for drive shortlisting",
    },
    "snap": {
        "label": "Snap / first impression",
        "description": "5-sec snap — early profile / first-impression signal",
    },
}

AREA_LABELS = {k: v["label"] for k, v in AREA_META.items() if k != "overall"}

TOOL_COVERAGE_SPEC: tuple[tuple[str, str], ...] = tuple(
    (s["tool_code"], s["title"]) for s in WEEK1_STEPS
)


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _iso(dt: Optional[datetime]) -> Optional[str]:
    if dt is None:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.isoformat()


def _mean(vals: list[float]) -> Optional[float]:
    if not vals:
        return None
    return round(sum(vals) / len(vals), 1)


def _pct(num: int, den: int) -> float:
    if den <= 0:
        return 0.0
    return round((num / den) * 100, 1)


def _build_tool_coverage(cards: list[StudentScorecard]) -> list[ToolCoverageItem]:
    total = len(cards)
    out: list[ToolCoverageItem] = []
    for tool, label in TOOL_COVERAGE_SPEC:
        completed = 0
        in_progress = 0
        remaining = 0
        for c in cards:
            st = (c.step_status_by_tool or {}).get(tool)
            if st == STEP_STATUS_DONE or tool in (c.scores_by_tool or {}):
                completed += 1
            elif st == STEP_STATUS_CURRENT:
                in_progress += 1
            else:
                remaining += 1
        out.append(
            ToolCoverageItem(
                tool=tool,
                label=label,
                completed=completed,
                in_progress=in_progress,
                remaining=remaining,
                total=total,
                pct=_pct(completed, total),
            )
        )
    return out


def _shortlist_score(
    readiness: Optional[float],
    tech: Optional[float],
    comm: Optional[float],
    coding: Optional[float] = None,
) -> Optional[float]:
    vals = [v for v in (readiness, tech, comm, coding) if v is not None]
    return _mean(vals)


def _area_score(card: StudentScorecard, area: str) -> Optional[float]:
    if area == "overall":
        return card.readiness
    if area == "shortlist":
        return card.shortlist_score
    if area == "communication":
        return card.communication_score
    if area == "technical":
        return card.technical_score
    if area == "coding":
        return (card.scores_by_tool or {}).get("coding")
    return _pillar_score(card.scores_by_tool, area)


def _to_ranked(card: StudentScorecard, rank: int, score: Optional[float]) -> RankedStudent:
    return RankedStudent(
        rank=rank,
        id=card.id,
        name=card.name,
        email=card.email,
        department_id=card.department_id,
        department_name=card.department_name,
        score=score,
        readiness=card.readiness,
        strength=card.strength,
        weakness=card.weakness,
        best_area=card.best_area,
        tests_done=card.tests_done,
        tests_remaining=card.tests_remaining,
        progress_level=card.progress_level,
        activity_status=card.activity_status,
    )


def _build_area_boards(cards: list[StudentScorecard], *, limit: int) -> list[AreaBoard]:
    boards: list[AreaBoard] = []
    for area, meta in AREA_META.items():
        scored_pairs: list[tuple[StudentScorecard, float]] = []
        for c in cards:
            score = _area_score(c, area)
            if score is None:
                continue
            scored_pairs.append((c, float(score)))
        scored_pairs.sort(key=lambda x: x[1], reverse=True)
        top = [_to_ranked(c, i + 1, s) for i, (c, s) in enumerate(scored_pairs[:limit])]
        prep_sorted = sorted(scored_pairs, key=lambda x: x[1])
        # Prefer less-prepared (<55) when available, else bottom of ranked list
        prep_pool = [(c, s) for c, s in prep_sorted if s < 55] or prep_sorted
        less_prepared = [
            _to_ranked(c, i + 1, s)
            for i, (c, s) in enumerate(prep_pool[:limit])
        ]
        boards.append(
            AreaBoard(
                area=area,
                label=meta["label"],
                description=meta["description"],
                students_scored=len(scored_pairs),
                avg_score=_mean([s for _, s in scored_pairs]),
                top=top,
                less_prepared=less_prepared,
            )
        )
    return boards


def _build_level_funnel(cards: list[StudentScorecard]) -> list[LevelFunnelItem]:
    total = len(cards) or 1
    out: list[LevelFunnelItem] = []
    for meta in WEEK1_STEPS:
        level = int(meta["order"])
        tool = meta["tool_code"]
        completed = sum(1 for c in cards if c.progress_level >= level or tool in (c.scores_by_tool or {}))
        # "reached" = completed this step OR currently on it OR progressed past it
        reached = sum(
            1
            for c in cards
            if c.progress_level >= level
            or (c.step_status_by_tool or {}).get(tool) in (STEP_STATUS_DONE, STEP_STATUS_CURRENT)
            or tool in (c.scores_by_tool or {})
        )
        done_exact = sum(
            1
            for c in cards
            if (c.step_status_by_tool or {}).get(tool) == STEP_STATUS_DONE
            or tool in (c.scores_by_tool or {})
        )
        out.append(
            LevelFunnelItem(
                level=level,
                label=str(meta["title"]),
                tool=tool,
                reached_or_beyond=reached,
                completed=done_exact,
                pct_completed=_pct(done_exact, total),
            )
        )
    return out


def _build_tests_aggregate(cards: list[StudentScorecard]) -> TestsAggregate:
    if not cards:
        return TestsAggregate(tools_total=TOOLS_TOTAL)
    done_vals = [c.tests_done for c in cards]
    rem_vals = [c.tests_remaining for c in cards]
    return TestsAggregate(
        tools_total=TOOLS_TOTAL,
        avg_tests_done=round(sum(done_vals) / len(cards), 2),
        avg_tests_remaining=round(sum(rem_vals) / len(cards), 2),
        students_all_done=sum(1 for c in cards if c.tests_done >= TOOLS_TOTAL),
        students_none_done=sum(1 for c in cards if c.tests_done <= 0),
        total_completions=sum(done_vals),
        total_remaining=sum(rem_vals),
    )


def _build_clarity(
    *,
    scope: str,
    students_total: int,
    students_scored: int,
    coverage_pct: float,
    drive_ready_pct: float,
    avg_readiness: Optional[float],
    bands: PerformanceBands,
    pillars: PillarAverages,
    top_gaps: list[GapStrengthItem],
    top_strengths: list[GapStrengthItem],
    active_7d: int,
    inactive_14d: int,
    never_started: int,
    at_risk_n: int,
    hod_gaps: int,
    by_department: list[DeptPerformanceRow],
) -> ClarityBoard:
    going_well: list[str] = []
    concerns: list[str] = []
    priorities: list[str] = []

    if students_scored and avg_readiness is not None and avg_readiness >= 65:
        going_well.append(f"Average readiness is solid at {avg_readiness}% across scored students.")
    if bands.strong > 0:
        going_well.append(
            f"{bands.strong} student(s) are drive-ready (≥75%) — {drive_ready_pct}% of the cohort."
        )
    if top_strengths:
        going_well.append(
            f"Strongest signal: {top_strengths[0].label} ({top_strengths[0].count} students)."
        )
    if active_7d > 0 and students_total:
        going_well.append(f"{active_7d} student(s) practiced in the last 7 days.")

    lagging_pillar = None
    pillar_pairs = [
        ("Aptitude", pillars.aptitude),
        ("Skills", pillars.skills),
        ("Interview", pillars.interview),
        ("5-sec snap", pillars.snap),
    ]
    scored_pillars = [(n, v) for n, v in pillar_pairs if v is not None]
    if scored_pillars:
        lagging_pillar = min(scored_pillars, key=lambda x: x[1])
        strong_pillar = max(scored_pillars, key=lambda x: x[1])
        if strong_pillar[1] >= 70:
            going_well.append(f"{strong_pillar[0]} leads pillars at {strong_pillar[1]}%.")

    if coverage_pct < 60:
        concerns.append(
            f"Only {coverage_pct}% of students have a readiness score — baseline coverage is incomplete."
        )
    if bands.weak > 0:
        concerns.append(
            f"{bands.weak} student(s) are less prepared (<50% readiness) and need focused practice."
        )
    if inactive_14d > 0:
        concerns.append(f"{inactive_14d} student(s) have been inactive for 14+ days.")
    if never_started > 0:
        concerns.append(f"{never_started} student(s) never started the baseline journey.")
    if top_gaps:
        concerns.append(
            f"Top preparation gap: {top_gaps[0].label} ({top_gaps[0].count} students)."
        )
    if lagging_pillar and lagging_pillar[1] < 55:
        concerns.append(
            f"Lowest pillar readiness is {lagging_pillar[0]} at {lagging_pillar[1]}%."
        )
    if scope == "organization" and hod_gaps:
        concerns.append(f"{hod_gaps} department(s) still lack an active HOD.")

    if at_risk_n > 0:
        focus = top_gaps[0].label if top_gaps else "fundamentals"
        priorities.append(
            f"Assign targeted practice for {at_risk_n} less-prepared student(s) — focus on {focus}."
        )
    if never_started > 0:
        priorities.append(f"Onboard the {never_started} never-started student(s) onto Week-1 baseline tools.")
    if inactive_14d > 0:
        priorities.append(f"Re-engage {inactive_14d} inactive student(s) with a short mock or snap check.")
    if lagging_pillar and lagging_pillar[1] < 60:
        priorities.append(
            f"Run a {lagging_pillar[0]} sprint for developing and less-prepared bands."
        )
    if scope == "organization":
        lagging_depts = sorted(
            [d for d in by_department if d.avg_readiness is not None],
            key=lambda d: float(d.avg_readiness or 0),
        )
        if lagging_depts and (lagging_depts[0].avg_readiness or 0) < 55:
            d0 = lagging_depts[0]
            priorities.append(
                f"Escalate {d0.name} ({d0.avg_readiness}% avg, {d0.weak} less prepared) to the HOD."
            )
        if hod_gaps:
            priorities.append(f"Close {hod_gaps} HOD gap(s) so every branch has a mentor owner.")
    if not priorities:
        priorities.append("Maintain weekly readiness checks and keep drive-ready students mock-sharp.")

    if not going_well:
        going_well.append("Cohort is set up — keep inviting and scoring students to build the picture.")
    if not concerns:
        concerns.append("No critical red flags in the current window — keep monitoring coverage and activity.")

    status: str = "watch"
    if at_risk_n >= max(3, students_total // 5) or coverage_pct < 40 or inactive_14d >= max(5, students_total // 4):
        status = "critical"
    elif (avg_readiness or 0) >= 65 and bands.weak <= max(1, students_total // 10) and coverage_pct >= 70:
        status = "healthy"

    return ClarityBoard(
        going_well=going_well[:5],
        concerns=concerns[:5],
        priorities=priorities[:5],
        status=status,  # type: ignore[arg-type]
    )


def _resolve_scope(
    ctx: TenantContext, department_id: Optional[int]
) -> tuple[str, Optional[int]]:
    if ctx.sees_all_students:
        return "organization", department_id
    if ctx.department_id is None:
        return "department", None
    return "department", ctx.department_id


async def _student_query(
    db: AsyncSession,
    org_id: int,
    department_id: Optional[int],
) -> list[User]:
    stmt = (
        select(User)
        .join(Role, User.role_id == Role.id)
        .where(User.organization_id == org_id)
        .where(Role.role_code == RoleCode.STUDENT.value)
        .where(User.status == UserStatus.ACTIVE.value)
        .where(User.deleted_at.is_(None))
        .options(selectinload(User.department))
        .order_by(User.name.asc())
    )
    if department_id is not None:
        stmt = stmt.where(User.department_id == department_id)
    return list((await db.execute(stmt)).scalars().all())


async def _weeks_by_user(
    db: AsyncSession, user_ids: list[int]
) -> dict[int, StudentRoadmapWeek]:
    if not user_ids:
        return {}
    stmt = (
        select(StudentRoadmapWeek)
        .where(StudentRoadmapWeek.user_id.in_(user_ids))
        .where(StudentRoadmapWeek.week_number == WEEK1_NUMBER)
        .options(selectinload(StudentRoadmapWeek.steps))
    )
    rows = list((await db.execute(stmt)).scalars().all())
    return {w.user_id: w for w in rows}


async def _attempt_counts(db: AsyncSession, user_ids: list[int]) -> dict[int, int]:
    if not user_ids:
        return {}
    stmt = (
        select(StudentAssessmentResult.user_id, func.count())
        .where(StudentAssessmentResult.user_id.in_(user_ids))
        .group_by(StudentAssessmentResult.user_id)
    )
    return {int(uid): int(cnt) for uid, cnt in (await db.execute(stmt)).all()}


async def _best_coding_scores(db: AsyncSession, user_ids: list[int]) -> dict[int, float]:
    """Best official coding submission score per student (for org dashboards)."""
    if not user_ids:
        return {}
    try:
        from app.coding.models import CodingSubmission
    except Exception:  # noqa: BLE001
        return {}
    stmt = (
        select(CodingSubmission.student_id, func.max(CodingSubmission.score))
        .where(CodingSubmission.student_id.in_(user_ids))
        .where(CodingSubmission.score.is_not(None))
        .group_by(CodingSubmission.student_id)
    )
    rows = (await db.execute(stmt)).all()
    return {int(uid): round(float(score), 1) for uid, score in rows if score is not None}


async def _latest_result_raw_by_user(
    db: AsyncSession, user_ids: list[int]
) -> dict[int, list[StudentAssessmentResult]]:
    """Latest assessment results per user (for tech/comm backfill from raw_json)."""
    if not user_ids:
        return {}
    stmt = (
        select(StudentAssessmentResult)
        .where(StudentAssessmentResult.user_id.in_(user_ids))
        .order_by(StudentAssessmentResult.created_at.desc())
    )
    rows = list((await db.execute(stmt)).scalars().all())
    out: dict[int, list[StudentAssessmentResult]] = defaultdict(list)
    seen: set[tuple[int, str]] = set()
    for r in rows:
        key = (int(r.user_id), str(r.tool_code))
        if key in seen:
            continue
        seen.add(key)
        out[int(r.user_id)].append(r)
    return out


def _pillar_score(scores_by_tool: dict[str, float], pillar: str) -> Optional[float]:
    tools = PILLAR_TOOLS.get(pillar) or ()
    vals = [scores_by_tool[t] for t in tools if t in scores_by_tool]
    return _mean(vals)


def _best_area(scores_by_tool: dict[str, float], tech: Optional[float], comm: Optional[float]) -> Optional[str]:
    candidates: list[tuple[str, float]] = []
    for key in ("aptitude", "skills", "interview", "snap", "coding"):
        if key == "coding":
            if "coding" in scores_by_tool:
                candidates.append(("coding", float(scores_by_tool["coding"])))
            continue
        v = _pillar_score(scores_by_tool, key)
        if v is not None:
            candidates.append((key, v))
    if tech is not None:
        candidates.append(("technical", tech))
    if comm is not None:
        candidates.append(("communication", comm))
    if not candidates:
        return None
    candidates.sort(key=lambda x: x[1], reverse=True)
    return candidates[0][0]


def _activity_status(days_inactive: Optional[int], activities: int) -> str:
    if activities <= 0 or days_inactive is None:
        return "never"
    if days_inactive <= 7:
        return "active"
    if days_inactive <= 14:
        return "idle"
    return "inactive"


def _scorecard_from_week(
    user: User,
    week: Optional[StudentRoadmapWeek],
    attempts: int,
    *,
    coding_score: Optional[float] = None,
    result_rows: Optional[list[StudentAssessmentResult]] = None,
) -> StudentScorecard:
    from app.student_roadmap.normalize import extract_scores_from_raw

    dept = user.department
    scores_by_tool: dict[str, float] = {}
    step_status_by_tool: dict[str, str] = {}
    strengths: list[str] = []
    weaknesses: list[str] = []
    tech_vals: list[float] = []
    comm_vals: list[float] = []
    last_active: Optional[datetime] = None
    activities = 0
    tests_done = 0
    tests_in_progress = 0
    tests_remaining = 0
    progress_level = 0

    raw_by_tool: dict[str, dict] = {}
    for r in result_rows or []:
        if isinstance(r.raw_json, dict):
            raw_by_tool[str(r.tool_code)] = r.raw_json
        # Prefer explicit columns on results when step columns are thin
        if r.technical_score is not None:
            tech_vals.append(float(r.technical_score))
        if r.communication_score is not None:
            comm_vals.append(float(r.communication_score))

    if week is not None:
        for step in week.steps or []:
            status = step.status or STEP_STATUS_LOCKED
            step_status_by_tool[step.tool_code] = status
            meta = TOOL_META.get(step.tool_code) or {}
            order = int(meta.get("order") or 0)
            if status == STEP_STATUS_DONE:
                tests_done += 1
                activities += 1
                if order > progress_level:
                    progress_level = order
                if step.score is not None:
                    scores_by_tool[step.tool_code] = float(step.score)
                for s in step.strengths_json or []:
                    if isinstance(s, str) and s.strip():
                        strengths.append(s.strip())
                for w in step.weaknesses_json or []:
                    if isinstance(w, str) and w.strip():
                        weaknesses.append(w.strip())
                if step.technical_score is not None:
                    tech_vals.append(float(step.technical_score))
                elif step.tool_code in raw_by_tool:
                    hydrated = extract_scores_from_raw(raw_by_tool[step.tool_code])
                    if hydrated.get("technical_score") is not None:
                        tech_vals.append(float(hydrated["technical_score"]))
                    if step.score is None and hydrated.get("score") is not None:
                        scores_by_tool[step.tool_code] = float(hydrated["score"])
                    for s in hydrated.get("strengths") or []:
                        strengths.append(str(s))
                    for w in hydrated.get("weaknesses") or []:
                        weaknesses.append(str(w))
                if step.communication_score is not None:
                    comm_vals.append(float(step.communication_score))
                elif step.tool_code in raw_by_tool:
                    hydrated = extract_scores_from_raw(raw_by_tool[step.tool_code])
                    if hydrated.get("communication_score") is not None:
                        comm_vals.append(float(hydrated["communication_score"]))
                if step.completed_at is not None:
                    ct = step.completed_at
                    if ct.tzinfo is None:
                        ct = ct.replace(tzinfo=timezone.utc)
                    if last_active is None or ct > last_active:
                        last_active = ct
            elif status == STEP_STATUS_CURRENT:
                tests_in_progress += 1
                if order > progress_level:
                    progress_level = max(progress_level, order - 1)
            else:
                tests_remaining += 1
    else:
        tests_remaining = TOOLS_TOTAL

    # Normalize remaining if week had partial steps only
    accounted = tests_done + tests_in_progress + tests_remaining
    if week is not None and accounted < TOOLS_TOTAL:
        tests_remaining += TOOLS_TOTAL - accounted

    if coding_score is not None:
        scores_by_tool["coding"] = float(coding_score)
        activities = max(activities, 1)

    readiness = _mean(list(scores_by_tool.values())) if scores_by_tool else None
    mock_vals = [scores_by_tool[t] for t in MOCK_TOOLS if t in scores_by_tool]
    mock_score = _mean(mock_vals)
    tech = _mean(tech_vals)
    comm = _mean(comm_vals)
    shortlist = _shortlist_score(readiness, tech, comm, coding_score)
    strength = Counter(strengths).most_common(1)[0][0] if strengths else None
    weakness = Counter(weaknesses).most_common(1)[0][0] if weaknesses else None
    days_inactive = None
    if last_active is not None:
        days_inactive = max(0, (_now() - last_active).days)

    return StudentScorecard(
        id=user.id,
        name=user.name or user.email or f"Student {user.id}",
        email=user.email,
        department_id=user.department_id,
        department_name=dept.name if dept else None,
        readiness=readiness,
        mock_score=mock_score,
        technical_score=tech,
        communication_score=comm,
        shortlist_score=shortlist,
        scores_by_tool=scores_by_tool,
        step_status_by_tool=step_status_by_tool,
        strength=strength,
        weakness=weakness,
        strengths=list(dict.fromkeys(strengths))[:8],
        weaknesses=list(dict.fromkeys(weaknesses))[:8],
        activities=activities,
        attempts=attempts,
        tests_done=tests_done,
        tests_in_progress=tests_in_progress,
        tests_remaining=tests_remaining,
        progress_level=progress_level,
        progress_pct=_pct(tests_done, TOOLS_TOTAL),
        week_status=week.status if week else None,
        last_active_at=_iso(last_active),
        days_inactive=days_inactive,
        activity_status=_activity_status(days_inactive, activities),
        best_area=_best_area(scores_by_tool, tech, comm),
    )


async def _pending_invites(db: AsyncSession, org_id: int, department_id: Optional[int]) -> int:
    stmt = (
        select(func.count())
        .select_from(User)
        .join(Role, User.role_id == Role.id)
        .where(User.organization_id == org_id)
        .where(Role.role_code == RoleCode.STUDENT.value)
        .where(User.status == UserStatus.PENDING.value)
        .where(User.deleted_at.is_(None))
    )
    if department_id is not None:
        stmt = stmt.where(User.department_id == department_id)
    return int((await db.execute(stmt)).scalar_one() or 0)


async def _upcoming_drives(db: AsyncSession, org_id: int) -> int:
    today = date.today()
    stmt = (
        select(func.count())
        .select_from(UpcomingDrive)
        .where(UpcomingDrive.organization_id == org_id)
        .where(UpcomingDrive.deleted_at.is_(None))
        .where(UpcomingDrive.drive_date >= today)
    )
    return int((await db.execute(stmt)).scalar_one() or 0)


async def _departments(db: AsyncSession, org_id: int, department_id: Optional[int]) -> list[Department]:
    stmt = (
        select(Department)
        .where(Department.organization_id == org_id)
        .where(Department.deleted_at.is_(None))
        .order_by(Department.name.asc())
    )
    if department_id is not None:
        stmt = stmt.where(Department.id == department_id)
    return list((await db.execute(stmt)).scalars().all())


async def _hod_status_map(db: AsyncSession, org_id: int) -> dict[int, str]:
    stmt = (
        select(User.department_id, User.status)
        .join(Role, User.role_id == Role.id)
        .where(User.organization_id == org_id)
        .where(Role.role_code == RoleCode.DEPARTMENT_ADMIN.value)
        .where(User.deleted_at.is_(None))
        .where(User.department_id.is_not(None))
    )
    out: dict[int, str] = {}
    for dept_id, status in (await db.execute(stmt)).all():
        if dept_id is None:
            continue
        # Prefer ACTIVE over PENDING if multiple
        prev = out.get(int(dept_id))
        if prev == UserStatus.ACTIVE.value:
            continue
        out[int(dept_id)] = str(status)
    return out


async def list_scorecards(
    db: AsyncSession,
    ctx: TenantContext,
    *,
    department_id: Optional[int] = None,
) -> ScorecardListOut:
    scope, dept_id = _resolve_scope(ctx, department_id)
    if scope == "department" and dept_id is None:
        return ScorecardListOut(scope="department", total=0, items=[])

    students = await _student_query(db, ctx.organization_id, dept_id)
    user_ids = [u.id for u in students]
    weeks = await _weeks_by_user(db, user_ids)
    attempts = await _attempt_counts(db, user_ids)
    coding_best = await _best_coding_scores(db, user_ids)
    results_by_user = await _latest_result_raw_by_user(db, user_ids)
    items = [
        _scorecard_from_week(
            u,
            weeks.get(u.id),
            attempts.get(u.id, 0),
            coding_score=coding_best.get(u.id),
            result_rows=results_by_user.get(u.id),
        )
        for u in students
    ]
    items.sort(key=lambda s: (s.readiness is not None, s.readiness or 0), reverse=True)
    return ScorecardListOut(scope=scope, total=len(items), items=items)


async def get_performance_summary(
    db: AsyncSession,
    ctx: TenantContext,
    *,
    department_id: Optional[int] = None,
    leaderboard_limit: int = 8,
    board_limit: int = 10,
) -> PerformanceSummaryOut:
    cards = await list_scorecards(db, ctx, department_id=department_id)
    scope = cards.scope
    dept_id = department_id if scope == "organization" else (
        ctx.department_id if scope == "department" else None
    )
    if scope == "department":
        dept_id = ctx.department_id

    scored = [c for c in cards.items if c.readiness is not None]
    bands = PerformanceBands(unscored=len(cards.items) - len(scored))
    for c in scored:
        r = float(c.readiness or 0)
        if r >= 75:
            bands.strong += 1
        elif r >= 50:
            bands.mid += 1
        else:
            bands.weak += 1

    gap_counter: Counter[str] = Counter()
    strength_counter: Counter[str] = Counter()
    pillar_vals: dict[str, list[float]] = defaultdict(list)
    active_7d = 0
    inactive_14d = 0
    never_started = 0
    idle_count = 0

    for c in cards.items:
        for g in c.weaknesses:
            gap_counter[g] += 1
        for s in c.strengths:
            strength_counter[s] += 1
        for pillar in ("aptitude", "skills", "interview", "snap"):
            v = _pillar_score(c.scores_by_tool, pillar)
            if v is not None:
                pillar_vals[pillar].append(v)
        if c.technical_score is not None:
            pillar_vals["technical"].append(float(c.technical_score))
        if c.communication_score is not None:
            pillar_vals["communication"].append(float(c.communication_score))

        if c.activity_status == "never":
            never_started += 1
        elif c.activity_status == "active":
            active_7d += 1
        elif c.activity_status == "inactive":
            inactive_14d += 1
        elif c.activity_status == "idle":
            idle_count += 1

    pillars = PillarAverages(
        aptitude=_mean(pillar_vals["aptitude"]),
        skills=_mean(pillar_vals["skills"]),
        interview=_mean(pillar_vals["interview"]),
        snap=_mean(pillar_vals["snap"]),
        communication=_mean(pillar_vals["communication"]),
        technical=_mean(pillar_vals["technical"]),
        shortlist=_mean(
            [float(c.shortlist_score) for c in cards.items if c.shortlist_score is not None]
        ),
    )

    top_gaps = [
        GapStrengthItem(label=k, count=v, share_pct=_pct(v, max(1, len(scored))))
        for k, v in gap_counter.most_common(8)
    ]
    top_strengths = [
        GapStrengthItem(label=k, count=v, share_pct=_pct(v, max(1, len(scored))))
        for k, v in strength_counter.most_common(8)
    ]

    # Always honor TPO department filter (and HOD scope) — never leak other depts' zeros
    depts = await _departments(db, ctx.organization_id, dept_id)
    hod_map = await _hod_status_map(db, ctx.organization_id)
    by_dept_cards: dict[Optional[int], list[StudentScorecard]] = defaultdict(list)
    for c in cards.items:
        by_dept_cards[c.department_id].append(c)

    by_department: list[DeptPerformanceRow] = []
    for d in depts:
        rows = by_dept_cards.get(d.id, [])
        scored_rows = [r for r in rows if r.readiness is not None]
        strong = mid = weak = active = inactive = never = 0
        dept_gap_counter: Counter[str] = Counter()
        for r in scored_rows:
            val = float(r.readiness or 0)
            if val >= 75:
                strong += 1
            elif val >= 50:
                mid += 1
            else:
                weak += 1
        for r in rows:
            if r.activity_status == "active":
                active += 1
            elif r.activity_status == "inactive":
                inactive += 1
            elif r.activity_status == "never":
                never += 1
            for g in r.weaknesses:
                dept_gap_counter[g] += 1
        by_department.append(
            DeptPerformanceRow(
                id=d.id,
                code=d.code,
                name=d.name,
                students=len(rows),
                scored_students=len(scored_rows),
                coverage_pct=_pct(len(scored_rows), len(rows)),
                avg_readiness=_mean([float(r.readiness) for r in scored_rows if r.readiness is not None]),
                avg_mock=_mean([float(r.mock_score) for r in scored_rows if r.mock_score is not None]),
                strong=strong,
                mid=mid,
                weak=weak,
                active_7d=active,
                inactive_14d=inactive,
                never_started=never,
                avg_tests_done=_mean([float(r.tests_done) for r in rows]) if rows else None,
                top_gap=dept_gap_counter.most_common(1)[0][0] if dept_gap_counter else None,
                hod_status=hod_map.get(d.id),
            )
        )

    # Least-prepared departments first — TPO action ordering
    by_department.sort(
        key=lambda d: (
            d.avg_readiness is None,
            float(d.avg_readiness) if d.avg_readiness is not None else 0.0,
        )
    )

    hod_gaps = sum(1 for d in by_department if not d.hod_status or d.hod_status != UserStatus.ACTIVE.value)

    def to_leader(c: StudentScorecard) -> LeaderboardEntry:
        return LeaderboardEntry(
            id=c.id,
            name=c.name,
            department_id=c.department_id,
            department_name=c.department_name,
            readiness=float(c.readiness or 0),
            mock_score=c.mock_score,
            strength=c.strength,
            weakness=c.weakness,
            best_area=c.best_area,
            activities=c.activities,
            tests_done=c.tests_done,
            progress_level=c.progress_level,
            last_active_at=c.last_active_at,
            days_inactive=c.days_inactive,
        )

    ranked = sorted(scored, key=lambda c: float(c.readiness or 0), reverse=True)
    leaders = [to_leader(c) for c in ranked[:leaderboard_limit]]
    at_risk = [
        to_leader(c)
        for c in sorted(scored, key=lambda c: float(c.readiness or 0))[:leaderboard_limit]
        if float(c.readiness or 0) < 50
    ]

    area_leaders: list[AreaLeader] = []
    for area, meta in AREA_META.items():
        if area == "overall":
            continue
        best: Optional[tuple[StudentScorecard, float]] = None
        for c in cards.items:
            score = _area_score(c, area)
            if score is None:
                continue
            if best is None or score > best[1]:
                best = (c, float(score))
        if best:
            c, score = best
            area_leaders.append(
                AreaLeader(
                    area=area,
                    label=meta["label"],
                    student_id=c.id,
                    student_name=c.name,
                    department_name=c.department_name,
                    score=score,
                )
            )
        else:
            area_leaders.append(AreaLeader(area=area, label=meta["label"]))

    board_n = max(3, min(50, int(board_limit or 10)))
    area_boards = _build_area_boards(cards.items, limit=board_n)
    level_funnel = _build_level_funnel(cards.items)
    tests_agg = _build_tests_aggregate(cards.items)

    pending = await _pending_invites(db, ctx.organization_id, dept_id)
    # Campus drives stay org-wide for TPO context even when a dept filter is on
    drives = await _upcoming_drives(db, ctx.organization_id) if scope == "organization" else 0

    total_n = len(cards.items)
    scored_n = len(scored)
    coverage_pct = _pct(scored_n, total_n)
    drive_ready_pct = _pct(bands.strong, total_n)
    drive_ready_of_scored_pct = _pct(bands.strong, scored_n)
    avg_readiness = _mean([float(c.readiness) for c in scored if c.readiness is not None])
    avg_mock = _mean([float(c.mock_score) for c in scored if c.mock_score is not None])
    tool_coverage = _build_tool_coverage(cards.items)
    coding_done = sum(1 for c in cards.items if (c.scores_by_tool or {}).get("coding") is not None)
    if total_n:
        tool_coverage.append(
            ToolCoverageItem(
                tool="coding",
                label="Coding assessment",
                completed=coding_done,
                in_progress=0,
                remaining=max(0, total_n - coding_done),
                total=total_n,
                pct=_pct(coding_done, total_n),
            )
        )
    # When TPO filters a department, treat clarity as branch-scoped for messaging
    clarity_scope = "department" if dept_id is not None else scope
    clarity = _build_clarity(
        scope=clarity_scope,
        students_total=total_n,
        students_scored=scored_n,
        coverage_pct=coverage_pct,
        drive_ready_pct=drive_ready_pct,
        avg_readiness=avg_readiness,
        bands=bands,
        pillars=pillars,
        top_gaps=top_gaps,
        top_strengths=top_strengths,
        active_7d=active_7d,
        inactive_14d=inactive_14d,
        never_started=never_started,
        at_risk_n=len(at_risk),
        hod_gaps=hod_gaps if clarity_scope == "organization" else 0,
        by_department=by_department,
    )

    return PerformanceSummaryOut(
        scope=scope,  # type: ignore[arg-type]
        organization_id=ctx.organization_id,
        department_id=dept_id,
        students_total=total_n,
        students_scored=scored_n,
        coverage_pct=coverage_pct,
        drive_ready_pct=drive_ready_pct,
        drive_ready_of_scored_pct=drive_ready_of_scored_pct,
        filtered_department_id=dept_id,
        avg_readiness=avg_readiness,
        avg_mock=avg_mock,
        bands=bands,
        pillars=pillars,
        tool_coverage=tool_coverage,
        level_funnel=level_funnel,
        tests=tests_agg,
        top_gaps=top_gaps,
        top_strengths=top_strengths,
        by_department=by_department,
        leaders=leaders,
        at_risk=at_risk,
        area_leaders=area_leaders,
        area_boards=area_boards,
        clarity=clarity,
        board_limit=board_n,
        active_7d=active_7d,
        idle_count=idle_count,
        inactive_14d=inactive_14d,
        never_started=never_started,
        pending_invites=pending,
        upcoming_drives=drives,
        hod_gaps=hod_gaps if scope == "organization" and dept_id is None else 0,
        generated_at=_iso(_now()) or "",
    )

"""Student read-only access to campus upcoming drives + prep helpers."""

from __future__ import annotations

from datetime import date, datetime, timezone

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.deps import get_db, require_api_key, require_roles
from app.models.enums import RoleCode
from app.models.upcoming_drive import UpcomingDrive
from app.models.user import User

router = APIRouter(
    prefix="/student/upcoming-drives",
    tags=["Student Company Prep"],
    dependencies=[Depends(require_api_key)],
)


class StudentDriveOut(BaseModel):
    id: int
    company_name: str
    eligibility_criteria: str
    drive_date: date
    remark: str | None = None
    days_until: int
    is_past: bool = False


class StudentDriveListOut(BaseModel):
    items: list[StudentDriveOut] = Field(default_factory=list)
    nearest: StudentDriveOut | None = None


def _days_until(drive_date: date, today: date) -> int:
    return (drive_date - today).days


@router.get("", response_model=StudentDriveListOut)
async def list_student_upcoming_drives(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_roles(RoleCode.STUDENT.value)),
) -> StudentDriveListOut:
    """Campus drives for the student's college (TPO-published)."""
    today = datetime.now(timezone.utc).date()
    rows = (
        await db.execute(
            select(UpcomingDrive)
            .where(UpcomingDrive.organization_id == user.organization_id)
            .where(UpcomingDrive.deleted_at.is_(None))
            .order_by(UpcomingDrive.drive_date.asc(), UpcomingDrive.id.desc())
        )
    ).scalars().all()

    items: list[StudentDriveOut] = []
    for row in rows:
        delta = _days_until(row.drive_date, today)
        items.append(
            StudentDriveOut(
                id=row.id,
                company_name=row.company_name,
                eligibility_criteria=row.eligibility_criteria,
                drive_date=row.drive_date,
                remark=row.remark,
                days_until=delta,
                is_past=delta < 0,
            )
        )

    # Students only see today/future drives — past dates are not listed.
    upcoming = [i for i in items if not i.is_past]
    nearest = upcoming[0] if upcoming else None
    return StudentDriveListOut(items=upcoming, nearest=nearest)

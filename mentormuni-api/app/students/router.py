"""
Student self-registration / enroll (college → PENDING).

POST /students/register
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.deps import get_db, require_api_key
from app.users import service as user_service
from app.users.schemas import StudentRegisterRequest, UserResponse
from app.users.router import _to_response

router = APIRouter(
    prefix="/students",
    tags=["Students"],
    dependencies=[Depends(require_api_key)],
)


@router.post("/register", response_model=UserResponse, status_code=201)
async def register_student(
    body: StudentRegisterRequest,
    response: Response,
    db: AsyncSession = Depends(get_db),
) -> UserResponse:
    """
    Public (API-key) college student enroll / register.

    Enroll-from-login body (no password) → PENDING for HOD/TPO queue.
    Legacy body with password still accepted.
    Idempotent for same email already PENDING in the college.
    """
    try:
        user, created = await user_service.register_student(
            db,
            email=str(body.email),
            department_id=body.department_id,
            organization_id=body.organization_id,
            organization_code=body.organization_code,
            name=body.name,
            first_name=body.first_name,
            last_name=body.last_name,
            username=body.username,
            password=body.password,
            mobile=body.mobile,
            phone=body.phone,
            roll_number=body.roll_number,
            batch_year=body.batch_year,
        )
    except user_service.UserServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc

    if not created:
        response.status_code = 200
    return _to_response(user)

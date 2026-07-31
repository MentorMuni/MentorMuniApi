"""Identity funnel dashboard schemas (Phase 2 — no assessment/AI metrics yet)."""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel


class DepartmentFunnelRow(BaseModel):
    department_id: int
    department_code: str
    department_name: str
    students_total: int
    students_pending: int
    students_active: int
    students_rejected: int
    students_blocked: int
    hod_count: int
    has_hod: bool


class DashboardIdentityResponse(BaseModel):
    organization_id: int
    role: str
    scope: str  # organization | department | self
    menu: list[str]
    departments_total: int
    departments_without_hod: int
    hods_total: int
    students_total: int
    students_pending: int
    students_active: int
    students_rejected: int
    students_blocked: int
    by_department: list[DepartmentFunnelRow]
    department_id: Optional[int] = None

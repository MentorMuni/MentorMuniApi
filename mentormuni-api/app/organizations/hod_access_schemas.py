"""HOD access policy schemas — Org Portal FE contract."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class HodAccessPolicy(BaseModel):
    can_invite_students: bool = True
    can_view_all_scores: bool = True
    can_assign_programs: bool = True
    can_notify_department: bool = True
    can_run_mocks: bool = True


class HodAccessResponse(HodAccessPolicy):
    organization_id: int
    updated_at: datetime | None = None


class HodAccessUpdate(BaseModel):
    can_invite_students: bool | None = None
    can_view_all_scores: bool | None = None
    can_assign_programs: bool | None = None
    can_notify_department: bool | None = None
    can_run_mocks: bool | None = None

    model_config = {"extra": "forbid"}


class HodAccessPatch(BaseModel):
    """Partial update with at least one field."""

    can_invite_students: bool | None = Field(default=None)
    can_view_all_scores: bool | None = Field(default=None)
    can_assign_programs: bool | None = Field(default=None)
    can_notify_department: bool | None = Field(default=None)
    can_run_mocks: bool | None = Field(default=None)

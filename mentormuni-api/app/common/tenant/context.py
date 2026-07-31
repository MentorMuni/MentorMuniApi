"""Tenant context extracted from JWT for every Org Portal request."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.models.user import User


@dataclass(frozen=True)
class TenantContext:
    """
    Source of truth for multi-tenant isolation.

    Never accept organization_id / department_id from the client body for authz.
    """

    user_id: int
    organization_id: int
    department_id: int | None
    role: str
    permissions: frozenset[str]
    user: "User"

    def has_permission(self, *codes: str) -> bool:
        if not codes:
            return True
        return bool(self.permissions.intersection(codes))

    @property
    def sees_all_students(self) -> bool:
        return "VIEW_ALL_STUDENTS" in self.permissions

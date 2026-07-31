"""Base tenant-aware repository helpers."""

from __future__ import annotations

from typing import Any, TypeVar

from sqlalchemy import Select, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import DeclarativeBase

from app.common.tenant.context import TenantContext

T = TypeVar("T", bound=DeclarativeBase)


class BaseTenantRepository:
    """
    All Org Portal data access should go through repositories that use this helper
    so organization_id (and dept/self when needed) is never forgotten.
    """

    def __init__(self, session: AsyncSession, ctx: TenantContext) -> None:
        self.session = session
        self.ctx = ctx

    def apply_org_scope(self, stmt: Select[Any], model: type[T]) -> Select[Any]:
        org_col = getattr(model, "organization_id", None)
        if org_col is None:
            return stmt
        return stmt.where(org_col == self.ctx.organization_id)

    def apply_soft_delete(self, stmt: Select[Any], model: type[T]) -> Select[Any]:
        deleted_col = getattr(model, "deleted_at", None)
        if deleted_col is None:
            return stmt
        return stmt.where(deleted_col.is_(None))

    def apply_department_scope_if_needed(
        self,
        stmt: Select[Any],
        model: type[T],
        *,
        force_department_id: int | None = None,
    ) -> Select[Any]:
        """
        If caller cannot VIEW_ALL_STUDENTS, restrict to their department
        (or an explicit department filter for TPO).
        """
        dept_col = getattr(model, "department_id", None)
        if dept_col is None:
            return stmt
        if force_department_id is not None:
            return stmt.where(dept_col == force_department_id)
        if not self.ctx.sees_all_students:
            if self.ctx.department_id is None:
                # No dept → empty result for dept-scoped resources
                return stmt.where(dept_col.is_(None)).where(dept_col.isnot(None))
            return stmt.where(dept_col == self.ctx.department_id)
        return stmt

    def scoped(
        self,
        stmt: Select[Any],
        model: type[T],
        *,
        department_id: int | None = None,
        apply_dept_rules: bool = False,
    ) -> Select[Any]:
        stmt = self.apply_org_scope(stmt, model)
        stmt = self.apply_soft_delete(stmt, model)
        if apply_dept_rules:
            stmt = self.apply_department_scope_if_needed(
                stmt, model, force_department_id=department_id
            )
        elif department_id is not None:
            dept_col = getattr(model, "department_id", None)
            if dept_col is not None:
                stmt = stmt.where(dept_col == department_id)
        return stmt

"""Who may assign / list campus programs (TPO + HOD)."""

from __future__ import annotations

from collections.abc import Coroutine
from typing import Any, Callable

from fastapi import Depends

from app.common.security.auth_errors import FORBIDDEN_ROLE, raise_forbidden
from app.common.tenant.context import TenantContext
from app.common.tenant.deps import get_tenant_context
from app.models.enums import RoleCode

_PROGRAM_ROLES = frozenset(
    {
        RoleCode.ORG_ADMIN.value,
        RoleCode.DEPARTMENT_ADMIN.value,
    }
)

_PROGRAM_PERMS = frozenset(
    {
        "ASSIGN_PROGRAM",
        "SEND_NOTIFICATION",
        "VIEW_REPORTS",
        "VIEW_DEPARTMENT_STUDENTS",
    }
)


def require_programs_access() -> Callable[..., Coroutine[Any, Any, TenantContext]]:
    """Org Admin or HOD with program-assignment permissions."""

    async def _checker(
        ctx: TenantContext = Depends(get_tenant_context),
    ) -> TenantContext:
        if ctx.role in _PROGRAM_ROLES:
            return ctx
        if ctx.has_permission(*_PROGRAM_PERMS):
            return ctx
        raise_forbidden(
            code=FORBIDDEN_ROLE,
            message=(
                "Only Org Admins (TPO / Dean / Director) and department HODs "
                "can assign programs."
            ),
        )

    return _checker

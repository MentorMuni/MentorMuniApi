"""Who may list / send campus notifications (TPO + HOD)."""

from __future__ import annotations

from collections.abc import Coroutine
from typing import Any, Callable

from fastapi import Depends

from app.common.security.auth_errors import FORBIDDEN_ROLE, raise_forbidden
from app.common.tenant.context import TenantContext
from app.common.tenant.deps import get_tenant_context
from app.models.enums import RoleCode

_CAMPUS_NOTIFY_ROLES = frozenset(
    {
        RoleCode.ORG_ADMIN.value,
        RoleCode.DEPARTMENT_ADMIN.value,
    }
)


def require_campus_notifications() -> Callable[..., Coroutine[Any, Any, TenantContext]]:
    """Org Admin (TPO/Dean/Director) or HOD — department scope enforced in service layer."""

    async def _checker(
        ctx: TenantContext = Depends(get_tenant_context),
    ) -> TenantContext:
        if ctx.role in _CAMPUS_NOTIFY_ROLES:
            return ctx
        if ctx.has_permission("SEND_NOTIFICATION"):
            return ctx
        raise_forbidden(
            code=FORBIDDEN_ROLE,
            message=(
                "Only Org Admins (TPO / Dean / Director) and department HODs "
                "can use campus notifications."
            ),
        )

    return _checker

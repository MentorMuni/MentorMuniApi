"""Permission checks for Org Portal endpoints."""

from __future__ import annotations

from collections.abc import Callable, Coroutine
from typing import Any

from fastapi import Depends

from app.common.security.auth_errors import FORBIDDEN_ROLE, raise_forbidden
from app.common.tenant.context import TenantContext
from app.common.tenant.deps import get_tenant_context


def require_permission(*codes: str) -> Callable[..., Coroutine[Any, Any, TenantContext]]:
    """
    Dependency: allow if TenantContext has any of the listed permission codes.
    """

    async def _checker(
        ctx: TenantContext = Depends(get_tenant_context),
    ) -> TenantContext:
        if codes and not ctx.has_permission(*codes):
            raise_forbidden(
                code=FORBIDDEN_ROLE,
                message=f"Missing permission. Requires one of: {', '.join(codes)}",
            )
        return ctx

    return _checker

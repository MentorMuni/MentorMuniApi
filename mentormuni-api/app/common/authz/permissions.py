"""Permission checks for Org Portal endpoints."""

from __future__ import annotations

from collections.abc import Callable, Coroutine
from typing import Any

from fastapi import Depends, HTTPException, status

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
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Missing permission. Requires one of: {', '.join(codes)}",
            )
        return ctx

    return _checker

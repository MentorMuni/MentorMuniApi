"""Load TenantContext for authenticated Org Portal users."""

from __future__ import annotations

from fastapi import Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.database.session import get_db
from app.common.deps import get_current_active_user
from app.common.tenant.context import TenantContext
from app.models.permission import Permission
from app.models.role_permission import RolePermission
from app.models.user import User


async def load_permissions_for_role(db: AsyncSession, role_id: int) -> frozenset[str]:
    result = await db.execute(
        select(Permission.permission_code)
        .join(RolePermission, RolePermission.permission_id == Permission.id)
        .where(RolePermission.role_id == role_id)
    )
    return frozenset(result.scalars().all())


async def build_tenant_context(db: AsyncSession, user: User) -> TenantContext:
    if user.role is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User has no role assigned.",
        )
    perms = await load_permissions_for_role(db, user.role_id)
    return TenantContext(
        user_id=user.id,
        organization_id=user.organization_id,
        department_id=user.department_id,
        role=user.role.role_code,
        permissions=perms,
        user=user,
    )


async def get_tenant_context(
    user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> TenantContext:
    return await build_tenant_context(db, user)

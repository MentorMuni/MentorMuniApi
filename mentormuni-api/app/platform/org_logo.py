"""Platform org logo upload / clear helpers."""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.organization import Organization
from app.platform.service import PlatformError, get_organization

ALLOWED_LOGO_TYPES = frozenset(
    {
        "image/png",
        "image/jpeg",
        "image/jpg",
        "image/webp",
        "image/svg+xml",
    }
)
MAX_LOGO_BYTES = 512 * 1024  # 512 KB


async def set_organization_logo(
    db: AsyncSession,
    organization_id: int,
    *,
    data: bytes,
    content_type: str,
) -> Organization:
    ct = (content_type or "").split(";")[0].strip().lower()
    if ct == "image/jpg":
        ct = "image/jpeg"
    if ct not in ALLOWED_LOGO_TYPES:
        raise PlatformError(
            f"Unsupported logo type '{content_type}'. Use PNG, JPEG, WebP, or SVG.",
            status_code=400,
        )
    if not data:
        raise PlatformError("Empty logo file.", status_code=400)
    if len(data) > MAX_LOGO_BYTES:
        raise PlatformError("Logo must be 512 KB or smaller.", status_code=400)

    org = await get_organization(db, organization_id)
    if str(org.organization_type).upper() == "PUBLIC":
        raise PlatformError(
            "PUBLIC organization does not use a campus logo.",
            status_code=400,
        )

    org.logo_bytes = data
    org.logo_content_type = ct
    org.logo_updated_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(org)
    return org


async def clear_organization_logo(db: AsyncSession, organization_id: int) -> Organization:
    org = await get_organization(db, organization_id)
    org.logo_bytes = None
    org.logo_content_type = None
    org.logo_updated_at = None
    await db.commit()
    await db.refresh(org)
    return org

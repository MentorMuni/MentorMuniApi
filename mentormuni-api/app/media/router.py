"""
Public media routes — no API key (img / favicon tags cannot send headers).

GET /media/organizations/{organization_id}/logo
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import undefer

from app.common.database.session import get_db
from app.models.organization import Organization

router = APIRouter(prefix="/media", tags=["Media"])


@router.get("/organizations/{organization_id}/logo")
async def get_organization_logo(
    organization_id: int,
    db: AsyncSession = Depends(get_db),
) -> Response:
    # logo_bytes is deferred — must undefer in the async SELECT.
    # Attribute access after db.get() raises MissingGreenlet under async SQLAlchemy.
    result = await db.execute(
        select(Organization)
        .where(Organization.id == organization_id)
        .options(undefer(Organization.logo_bytes))
    )
    org = result.scalar_one_or_none()
    if org is None or not org.logo_content_type:
        raise HTTPException(status_code=404, detail="Logo not found.")

    blob = org.logo_bytes
    if not blob:
        raise HTTPException(status_code=404, detail="Logo not found.")

    headers = {
        "Cache-Control": "public, max-age=86400",
    }
    if org.logo_updated_at is not None:
        headers["ETag"] = f'W/"{int(org.logo_updated_at.timestamp())}"'

    return Response(
        content=bytes(blob),
        media_type=org.logo_content_type,
        headers=headers,
    )

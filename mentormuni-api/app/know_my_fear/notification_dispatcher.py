"""Background dispatcher for private Fear → Fearless notifications."""

from __future__ import annotations

import asyncio
import logging
from typing import Optional

logger = logging.getLogger(__name__)

_task: Optional[asyncio.Task] = None
POLL_SECONDS = 60


def _db_ready() -> bool:
    try:
        from app.core.config import settings

        return bool(settings.is_database_configured)
    except Exception:
        return False


async def _loop() -> None:
    from app.common.database.session import async_session_factory
    from app.know_my_fear.intervention_service import InterventionService

    service = InterventionService()
    while True:
        try:
            if _db_ready():
                factory = async_session_factory()
                async with factory() as db:
                    count = await service.dispatch_due_notifications(db)
                    await db.commit()
                    if count:
                        logger.info("Fear → Fearless: sent %s due notifications", count)
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("Fear → Fearless notification dispatcher failed")
        await asyncio.sleep(POLL_SECONDS)


def start_notification_dispatcher() -> Optional[asyncio.Task]:
    """Start background loop; safe to call once from app lifespan."""
    global _task
    if _task and not _task.done():
        return _task
    if not _db_ready():
        logger.info("Skipping Fear → Fearless notification dispatcher (no DATABASE_URL)")
        return None
    _task = asyncio.create_task(_loop(), name="fear-to-fearless-notifications")
    logger.info("Started Fear → Fearless notification dispatcher (every %ss)", POLL_SECONDS)
    return _task


async def stop_notification_dispatcher() -> None:
    global _task
    if _task and not _task.done():
        _task.cancel()
        try:
            await _task
        except asyncio.CancelledError:
            pass
    _task = None

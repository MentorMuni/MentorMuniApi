"""CodingJobWorker — dedicated process (Railway worker service).

Never runs inside FastAPI request handlers / BackgroundTasks.
"""

from __future__ import annotations

import asyncio
import logging
import signal
from typing import Optional

# Ensure all ORM tables (users, orgs, …) are registered before CodingJob FKs resolve.
import app.models  # noqa: F401

from app.coding.jobs import queue as job_queue
from app.coding.jobs.handlers import handle_job
from app.coding.limits import get_coding_limits
from app.common.database.session import async_session_factory, close_db, init_db
from app.core.config import settings

logger = logging.getLogger("coding.worker")

_stop = False


def _request_stop(*_args: object) -> None:
    global _stop
    _stop = True
    logger.info("coding_worker_stop_requested")


async def process_once() -> bool:
    """Claim and process one job. Returns True if work was done."""
    factory = async_session_factory()
    async with factory() as db:
        try:
            await job_queue.recover_stale_jobs(db)
            job = await job_queue.claim_next_job(db)
            if job is None:
                await db.commit()
                return False
            await handle_job(db, job)
            await db.commit()
            return True
        except Exception:
            await db.rollback()
            logger.exception("coding_worker_iteration_failed")
            return True  # back off via sleep in loop


async def run_worker_loop(*, idle_sleep_ms: int | None = None) -> None:
    await init_db()
    if not settings.judge0_base_url:
        logger.warning("JUDGE0_BASE_URL is empty — run jobs will fail until configured")
    limits = get_coding_limits()
    sleep_ms = idle_sleep_ms if idle_sleep_ms is not None else limits.job_poll_interval_ms
    logger.info(
        "coding_worker_started max_concurrent=%s poll_ms=%s",
        limits.max_concurrent_jobs,
        sleep_ms,
    )
    while not _stop:
        worked = await process_once()
        if not worked:
            await asyncio.sleep(sleep_ms / 1000.0)
    await close_db()
    logger.info("coding_worker_stopped")


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )
    signal.signal(signal.SIGINT, _request_stop)
    signal.signal(signal.SIGTERM, _request_stop)
    asyncio.run(run_worker_loop())


if __name__ == "__main__":
    main()

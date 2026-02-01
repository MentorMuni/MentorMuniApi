import asyncio
import logging
from typing import TypeVar, Coroutine, Any

logger = logging.getLogger("guard_layer")
T = TypeVar("T")


class GuardLayer:
    def __init__(self, timeout: int = 30, max_retries: int = 3):
        self.timeout = timeout
        self.max_retries = max_retries

    async def run_with_timeout(self, coro: Coroutine[Any, Any, T]) -> T:
        """Run a coroutine with a timeout. Use this to wrap LLM calls."""
        try:
            return await asyncio.wait_for(coro, timeout=self.timeout)
        except asyncio.TimeoutError:
            logger.error("Request timed out.")
            raise TimeoutError("Request timed out. Please try again later.") from None

    async def retry_with_fallback(self, coro_func, *args, **kwargs):
        """Retry an async call with exponential backoff."""
        last_error = None
        for attempt in range(self.max_retries):
            try:
                coro = coro_func(*args, **kwargs)
                return await coro
            except Exception as e:
                last_error = e
                logger.warning("Attempt %d failed: %s", attempt + 1, e)
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(2 ** attempt)
        logger.error("All retry attempts failed.")
        raise RuntimeError("Service unavailable. Please try again later.") from last_error
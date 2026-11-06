"""Retry with exponential backoff, for network calls that have no retries of their own."""

import logging
import time
from collections.abc import Callable

log = logging.getLogger(__name__)


def retry[T](
    fn: Callable[[], T],
    *,
    what: str,
    retry_on: tuple[type[BaseException], ...] = (Exception,),
    retries: int = 3,
    base_delay: float = 1.0,
    sleep: Callable[[float], None] = time.sleep,
) -> T:
    """Call fn, retrying up to `retries` times on the given errors (1s, 2s, 4s by default)."""
    for attempt in range(retries + 1):
        try:
            return fn()
        except retry_on as error:
            if attempt == retries:
                raise
            delay = base_delay * 2**attempt
            log.warning("%s failed (%s); retry %d/%d in %.0fs", what, error, attempt + 1, retries, delay)
            sleep(delay)
    raise AssertionError("unreachable")

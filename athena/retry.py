"""Bounded retry for model calls: quota (429), server errors and deadline (5xx)."""

import logging
import time
from collections.abc import Callable
from typing import TypeVar

from google.genai import errors

T = TypeVar("T")
log = logging.getLogger("athena")

RETRYABLE = {429, 500, 502, 503, 504}
BACKOFF_S = (2, 6, 15)


def with_retry(fn: Callable[[], T], what: str, deadline: float | None = None) -> T:
    """deadline: time.monotonic() value after which no further retry starts."""
    for i, wait in enumerate((*BACKOFF_S, None)):
        try:
            return fn()
        except errors.APIError as e:
            out_of_time = deadline is not None and time.monotonic() + wait > deadline if wait else False
            if wait is None or e.code not in RETRYABLE or out_of_time:
                raise
            log.warning("%s: %s, retry %d in %ss", what, e.code, i + 1, wait)
            time.sleep(wait)
    raise AssertionError("unreachable")

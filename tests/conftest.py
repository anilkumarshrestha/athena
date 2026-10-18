"""Shared test setup."""

import pytest

from athena.ratelimit import RateLimit


@pytest.fixture(autouse=True)
def _fresh_rate_limits():
    """Each test starts with empty rate-limit windows: API tests in different files share the
    same limiter objects and the same client IP, so counts would otherwise carry over."""
    import athena.api as api

    for obj in vars(api).values():
        if isinstance(obj, RateLimit):
            with obj._lock:
                obj._hits.clear()
                obj._all.clear()
    yield

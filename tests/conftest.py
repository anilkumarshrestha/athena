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


@pytest.fixture(autouse=True)
def _no_writes_to_real_state(monkeypatch):
    """API tests run against the app's store: never write it to the real state/ directory."""
    from athena.store import store

    monkeypatch.setattr(store, "save", lambda: None)
    yield


@pytest.fixture
def own(monkeypatch):
    """own(client, learner): put a learner in this test client's family (as if it created it)."""
    from athena import family

    def _own(client, learner):
        fid = family.valid_code(client.get("/api/family").json()["code"])
        monkeypatch.setattr(learner, "family", fid)
        return fid

    return _own

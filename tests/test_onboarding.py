"""Onboarding answers become a profile that changes what the child gets."""

from athena.profile import personal_themes


def test_activity_becomes_a_personal_theme():
    themes = [t.text for t in personal_themes("cat", "momo", "kite")]
    assert "flying a kite with friends" in themes and len(themes) == 3
    assert len(personal_themes("cat", "momo", None)) == 2


def test_create_with_onboarding_answers(monkeypatch):
    from fastapi.testclient import TestClient

    import athena.api as api
    from athena.store import store

    monkeypatch.setattr(store, "save", lambda: None)
    c = TestClient(api.app)
    body = {"name_ne": "किरण", "name_en": "Kiran", "favorite_animal": "dog", "favorite_food": "momo", "setting": "city",
            "gender": "boy", "start": "beginner", "age": "5", "languages": "ne", "activity": "football",
            "buddy": "rabbit", "daily_goal": "15", "avatar": "elephant"}
    r = c.post("/api/learners", json=body)
    assert r.status_code == 201
    l = r.json()
    try:
        assert l["avatar"] == "elephant" and l["avatar_url"].endswith("हात्ती")
        assert l["profile"]["activity"] == "football" and l["profile"]["languages"] == "ne" and l["profile"]["buddy"] == "rabbit"
        r2 = c.post("/api/learners", json={k: v for k, v in body.items() if k != "avatar"}).json()  # skipped: a default
        store.learners.pop(r2["id"], None)
        assert r2["avatar"] in ("cat", "dog", "rabbit", "elephant", "monkey", "bear", "butterfly", "fish", "duck", "yak", "goat", "bird")
        assert c.put(f"/api/learners/{l['id']}/avatar", json={"avatar": "monkey"}).json()["avatar"] == "monkey"
        assert c.put(f"/api/learners/{l['id']}/avatar", json={"avatar": "dragon"}).status_code == 422
        assert l["level"]["ne"] == 1 and l["used_today"] == 0  # age 5: shortest stories
        assert c.post("/api/learners", json={**body, "buddy": "dragon"}).status_code == 422  # fixed choices only
    finally:
        store.learners.pop(l["id"], None)


def test_default_avatar_is_steady():
    from athena.profile import AVATARS, avatar_of

    assert avatar_of("abc123", None) == avatar_of("abc123", None) == avatar_of("abc123", "dragon")
    assert avatar_of("abc123", "fish") == "fish"
    assert {avatar_of(f"id{i}", None) for i in range(60)} <= set(AVATARS)

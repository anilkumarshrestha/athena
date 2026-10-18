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
            "buddy": "rabbit", "daily_goal": "15"}
    r = c.post("/api/learners", json=body)
    assert r.status_code == 201
    l = r.json()
    try:
        assert l["avatar"] == "rabbit" and l["profile"]["activity"] == "football" and l["profile"]["languages"] == "ne"
        assert l["level"]["ne"] == 1 and l["used_today"] == 0  # age 5: shortest stories
        assert c.post("/api/learners", json={**body, "buddy": "dragon"}).status_code == 422  # fixed choices only
    finally:
        store.learners.pop(l["id"], None)

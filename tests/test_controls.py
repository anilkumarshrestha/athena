"""Parent content controls: activities on/off, story pictures, themes to avoid."""

from athena.agents.planner import THEMES, plan
from athena.presets import preset


def test_planner_never_picks_an_avoided_theme():
    _, mastery = preset("ne_mid")
    avoid = frozenset(t.text for t in THEMES[1:])  # everything but the first
    themes = {plan("ne", mastery, "सीता", seed=i, avoid=avoid).theme for i in range(20)}
    assert themes == {THEMES[0].text}


def test_controls_api(monkeypatch, own):
    from fastapi.testclient import TestClient

    import athena.api as api
    from athena.store import store

    learner = store.get_learner("sita")
    monkeypatch.setattr(learner, "controls", dict(learner.controls))
    monkeypatch.setattr(store, "save", lambda: None)
    c = TestClient(api.app)
    own(c, learner)
    assert c.put(f"/api/learners/{learner.id}/controls", json={"avoid_themes": ["anything goes"]}).status_code == 422
    t = THEMES[0].text
    r = c.put(f"/api/learners/{learner.id}/controls", json={"maths": False, "teach": False, "pictures": False,
                                                            "avoid_themes": [t]})
    assert r.status_code == 200 and r.json()["controls"]["avoid_themes"] == [t]
    assert c.post("/api/maths/start", json={"learner_id": learner.id, "language": "ne"}).json()["detail"] == "maths_off"
    assert c.post(f"/api/learners/{learner.id}/teach/ne").json()["detail"] == "teach_off"
    assert all(ch["theme"] != t for ch in c.get(f"/api/learners/{learner.id}/choices/ne").json())
    assert len(c.get("/api/themes").json()) == len(THEMES)

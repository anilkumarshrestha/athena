"""Shelf: a demo child's first stories are served instantly, still checked against their letters."""

import json

from athena.history import History


def test_demo_child_gets_shelf_story_instantly(tmp_path, monkeypatch):
    from fastapi.testclient import TestClient

    import athena.api as api
    import athena.shelf as shelf
    from athena.store import store
    from tests.test_prefetch import fake_result

    monkeypatch.setattr(store, "history", History(tmp_path / "h"))
    c = TestClient(api.app)
    sita = next(x for x in c.get("/api/learners").json() if x["name"]["en"] == "Sita")
    learner = store.get_learner(sita["id"]) or store.learners[sita["id"]]
    # a two-story shelf for Sita (Nepali), readable with her letters, at her level
    sents = [["सीता घर गइन्।"], ["सीता रमाइन्।"]]
    items = [{"result": json.loads(fake_result(learner, s, level=learner.level["ne"]).model_dump_json()), "image": ""}
             for s in sents]
    monkeypatch.setattr(shelf, "SHELF", tmp_path)
    (tmp_path / "sita_ne.json").write_text(json.dumps(items, ensure_ascii=False), encoding="utf-8")
    shelf._load.cache_clear()
    monkeypatch.setattr(api, "_compose", lambda *a, **k: (_ for _ in ()).throw(AssertionError("composed live")))

    assert c.post(f"/api/learners/{learner.id}/warm").json()["ne"] == "shelf"
    s1 = c.post("/api/session/start", json={"learner_id": learner.id, "language": "ne"}).json()
    assert s1["sentences"] == ["सीता घर गइन्।"]  # served from the shelf, no model call
    assert c.post(f"/api/learners/{learner.id}/warm").json()["ne"] == "shelf"
    s2 = c.post("/api/session/start", json={"learner_id": learner.id, "language": "ne"}).json()
    assert s2["sentences"] == ["सीता रमाइन्।"]
    shelf._load.cache_clear()

"""Re-teach card learns the child: retries log the ways used; the card order follows them."""

from athena.history import History


def test_retry_logs_ways_and_reorders_the_card(tmp_path, monkeypatch, own):
    from fastapi.testclient import TestClient

    import athena.api as api
    from athena.assess import stt
    from athena.store import store
    from tests.test_prefetch import fake_result

    learner = store.get_learner("sita")
    monkeypatch.setattr(store, "history", History(tmp_path))
    story = store.add_story(learner.id, "ne", fake_result(learner, ["सीता घर गइन्।"]))
    store.history.append(learner.id, {"type": "story", "story_id": story.id, "at": 1.0, "lang": "ne"})
    monkeypatch.setattr(api.stt, "transcribe", lambda *a, **k: stt.Transcript(text=heard[0], engine="test", latency_ms=1))
    c = TestClient(api.app)
    own(c, learner)

    assert c.get(f"/api/stories/{story.id}/words/1").json()["styles"][0] == "hear"  # no evidence yet
    # hearing does not help this child; seeing the parts does
    for styles, said in [("hear", "गर"), ("hear", "गर"), ("hear,parts", "घर"), ("parts", "घर")]:
        heard = [said]
        r = c.post(f"/api/stories/{story.id}/words/1/read", files={"audio": ("w.webm", b"x" * 10, "audio/webm")},
                   data={"styles": styles + ",bogus"})
        assert r.status_code == 200
    logged = store.history.story(learner.id, story.id)["reteach"]
    assert [e["styles"] for e in logged] == [["hear"], ["hear"], ["hear", "parts"], ["parts"]]  # bogus dropped
    assert [e["correct"] for e in logged] == [False, False, True, True]
    assert c.get(f"/api/stories/{story.id}/words/1").json()["styles"][0] == "parts"
    assert c.get(f"/api/learners/{learner.id}/insights/ne").json()["helps_most"]["style"] == "parts"
    assert len(c.get(f"/api/learners/{learner.id}/stories/{story.id}").json()["reteach"]) == 4

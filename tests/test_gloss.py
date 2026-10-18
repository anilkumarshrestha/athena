"""English gloss for grown-ups: romanisation in code, translation cached."""

from athena.gloss import romanise


def test_romanise_reads_like_spoken_nepali():
    assert romanise("सीताको सानो खैरो खसी छ।") == "sītāko sāno khairo khasī cha."
    assert romanise("घर") == "ghar"  # word-final a is not said
    assert romanise("न") == "na"  # but one syllable keeps it
    assert romanise("अब कति किताब छन्?") == "ab kati kitāb chan?"
    assert romanise("राम्रो") == "rāmro"  # virama joins the consonants


def test_gloss_endpoint_only_for_this_familys_nepali_stories(monkeypatch, own):
    from fastapi.testclient import TestClient

    import athena.api as api
    import athena.gloss as g
    from athena.store import store
    from tests.test_prefetch import fake_result

    monkeypatch.setattr(g, "translate", lambda lines: [f"EN {i}" for i in range(len(lines))])
    learner = store.get_learner("sita")
    story = store.add_story(learner.id, "ne", fake_result(learner, ["सीता घर गइन्।"]))
    c, other = TestClient(api.app), TestClient(api.app)
    own(c, learner)
    r = c.get(f"/api/stories/{story.id}/gloss").json()
    assert r["sentences"][0] == {"text": "सीता घर गइन्।", "roman": "sītā ghar gain.", "english": "EN 1"}
    assert other.get(f"/api/stories/{story.id}/gloss").status_code == 404  # another family

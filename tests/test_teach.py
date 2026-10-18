"""Teach the cat: code-chosen audible mistakes; the child catches them."""

import random

from athena.history import History
from athena.teach import cat_answer, cat_sentences, en_changes, ne_changes, plan_mistakes, teach_summary


def test_changes_are_audible_only():
    kinds = {k for _, k, _ in ne_changes("दाल")}
    assert kinds == {"aspiration", "retroflex_dental", "vowel_sign"}
    for w in ("सीता", "किताब", "पानी", "दूध"):
        for new, _, _ in ne_changes(w):  # never a vowel-length or sibilant change: those sound the same
            assert "ी" not in new.replace("ी", "", w.count("ी")) and "ू" not in new.replace("ू", "", w.count("ू"))
            assert all(c not in new for c in "शष")
    assert ("sip", "digraph", "sh") in en_changes("ship")
    assert ("ded", "b_d", "b") in en_changes("bed")


def test_plan_prefers_the_childs_own_confusion_and_skips_the_name():
    words = ["सीता", "घर", "गइन्", "टोपी", "किनिन्"]
    m = plan_mistakes("ne", words, {"सीता"}, ["retroflex_dental"], set(), random.Random(0))
    assert len(m) == 2 and all(x["word"] != "सीता" for x in m)
    assert m[0]["kind"] == "retroflex_dental" or m[1]["kind"] == "retroflex_dental"
    assert m[0]["index"] + 1 < m[1]["index"]  # spread out


def test_cat_sentences_change_only_the_chosen_words():
    sentences = ["सीता घर गइन्।", "टोपी राम्रो छ।"]
    chunks = [[[0], [1], [2]], [[3], [4], [5]]]
    words = ["सीता", "घर", "गइन्", "टोपी", "राम्रो", "छ"]
    mistakes = [{"index": 1, "cat_word": "गर"}, {"index": 3, "cat_word": "तोपी"}]
    assert cat_sentences("ne", sentences, chunks, words, mistakes) == ["सीता गर गइन्।", "तोपी राम्रो छ।"]
    assert cat_sentences("en", ["The ship sat."], [[[0], [1], [2]]], ["the", "ship", "sat"],
                         [{"index": 1, "cat_word": "sip"}]) == ["The sip sat."]


def test_cat_maths_answer_uses_the_childs_mistake_and_is_sometimes_right():
    rng = random.Random(0)
    assert cat_answer(5, 2, "+", {}, 0, rng) == 7  # 1 in 3: right
    assert cat_answer(5, 2, "+", {"wrong_operation": 3}, 1, rng) == 3  # added -> took away
    assert cat_answer(5, 2, "+", {"off_by_one": 3}, 2, rng) in (6, 8)


def test_round_trip_through_the_api(tmp_path, monkeypatch):
    from fastapi.testclient import TestClient

    import athena.api as api
    from athena.store import store

    learner = store.get_learner("sita")
    monkeypatch.setattr(store, "history", History(tmp_path))
    c = TestClient(api.app)
    assert c.post(f"/api/learners/{learner.id}/teach/ne").status_code == 404  # nothing read yet
    store.history.append(learner.id, {"type": "story", "story_id": "s1", "at": 1.0, "lang": "ne", "title": "घर",
                                      "sentences": ["सीता घर गइन्।", "टोपी राम्रो छ।"]})
    store.history.append(learner.id, {"type": "reading", "story_id": "s1", "at": 2.0, "words": []})
    t = c.post(f"/api/learners/{learner.id}/teach/ne").json()
    assert t["mistakes"] == 2 and t["sentences"] == ["सीता घर गइन्।", "टोपी राम्रो छ।"]
    targets = [m["index"] for m in api._teach[t["id"]]["mistakes"]]
    api._teach.clear()  # restart: rebuilt from history
    miss = c.post(f"/api/teach/{t['id']}/tap", json={"index": 0}).json()  # the name: never changed
    assert miss["caught"] is False and miss["left"] == 2
    hit = c.post(f"/api/teach/{t['id']}/tap", json={"index": targets[0]}).json()
    assert hit["caught"] and hit["left"] == 1 and hit["word"]
    summary = c.get(f"/api/learners/{learner.id}/insights/ne").json()["teach_cat"]
    assert summary["rounds"] == 1 and summary["mistakes"] == 2 and summary["caught"] == 1
    assert teach_summary([], "ne") is None

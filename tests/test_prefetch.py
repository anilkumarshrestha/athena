"""Next story prepared after a reading, re-verified before it is served. Model mocked."""

from concurrent.futures import Future

import athena.api as api
from athena.agents.planner import plan
from athena.models import GenerationResult
from athena.presets import preset
from athena.store import store


def fake_result(learner, sentences, level=None):
    lang, m = "ne", frozenset(learner.mastery["ne"])
    p = plan(lang, m, learner.name["ne"], seed=1, level=level or learner.level["ne"])
    return GenerationResult(plan=p, attempts=[], outcome="first_pass", title=learner.name["ne"], sentences=sentences,
                            scene="", units_used=[], first_pass_violations=0, final_violation_count=0, total_latency_ms=0)


def prepared(learner, result):
    img = Future()
    img.set_exception(RuntimeError("no picture in tests"))
    done = Future()
    done.set_result((result, img))
    api._prefetch[(learner.id, "ne")] = (api.time.time(), done)


def test_valid_prepared_story_is_served(monkeypatch):
    sita = store.get_learner("sita")
    r = fake_result(sita, ["आमा घर छ।"])
    prepared(sita, r)
    assert api._take_prefetched(sita, "ne")[0] is r
    assert (sita.id, "ne") not in api._prefetch  # used once


def test_story_with_a_now_unreadable_unit_is_discarded():
    sita = store.get_learner("sita")
    prepared(sita, fake_result(sita, ["क्षमा घर छ।"]))  # क्ष: a conjunct Sita cannot read
    assert api._take_prefetched(sita, "ne") is None


def test_level_change_discards():
    sita = store.get_learner("sita")
    prepared(sita, fake_result(sita, ["आमा घर छ।"], level=sita.level["ne"] + 1))
    assert api._take_prefetched(sita, "ne") is None


def test_close_triggers_prefetch(monkeypatch):
    calls = []
    monkeypatch.setattr(api, "_compose", lambda learner, lang, theme=None: calls.append((learner.id, lang)))
    api._prefetch.clear()
    api._prefetch_next(store.get_learner("sita"), "ne")
    api._prefetch[("sita", "ne")][1].result(timeout=5)
    assert calls == [("sita", "ne")]
    api._prefetch.clear()

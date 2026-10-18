"""Story safety check: blocklist (code) + model screen (mocked here). Offline."""

from athena import safety


def test_blocklist_catches_words_and_inflections():
    assert safety.blocklisted("ne", ["बिरालो", "मर्यो"]) == ["मर्यो"]
    assert safety.blocklisted("ne", ["भूतले"]) == ["भूतले"]  # stem + case ending
    assert safety.blocklisted("en", ["The", "dog", "killed"]) == ["killed"]
    assert safety.blocklisted("en", ["Sam", "kicked", "the", "ball"]) == []  # games are fine


def test_clean_story_passes_blocklist():
    assert safety.blocklisted("ne", "सीता र आमा बजार जानुभयो".split()) == []
    assert safety.blocklisted("en", "Sam sat in a ship".split()) == []


def test_check_uses_blocklist_before_model(monkeypatch):
    calls = []
    monkeypatch.setattr(safety, "_model_screen", lambda lang, text: calls.append(text) or (True, ""))
    r = safety.check("en", "Ghost", ["The dog is dead."])
    assert not r.safe and r.stage == "blocklist" and calls == []  # model never called


def test_model_screen_result_is_used(monkeypatch):
    monkeypatch.setattr(safety, "_model_screen", lambda lang, text: (False, "child is left alone at night"))
    r = safety.check("en", "Night", ["Sam sat in the dark pit."])
    assert not r.safe and r.stage == "model" and "alone" in r.reason


def test_model_failure_fails_closed(monkeypatch):
    def boom(lang, text):
        raise RuntimeError("quota")

    monkeypatch.setattr(safety, "_model_screen", boom)
    r = safety.check("en", "Pan", ["Sam sat."])
    assert not r.safe and r.stage == "error"


def test_unsafe_story_is_replaced_never_shown(monkeypatch):
    from athena import generate as g
    from athena.agents import writer
    from athena.agents.planner import plan
    from athena.models import StoryDraft, Usage
    from athena.presets import preset

    draft = StoryDraft(title="सीता", sentences=["सीता घर गइन्।", "बाबा घर आउनुभयो।"], scene="x")
    monkeypatch.setattr(writer, "write", lambda p, f=None, t=None: (draft, "p", Usage(), 5))
    monkeypatch.setattr(safety, "_model_screen", lambda lang, text: (False, "test: unsafe"))
    lang, m = preset("ne_basic")
    r = g.generate(plan(lang, m, "सीता", seed=1, level=2), log=False)
    assert r.safety["replaced"] and r.safety["stage"] == "model"
    assert r.outcome in ("template", "wordlist")
    assert "सीता घर गइन्।" not in r.sentences
    assert r.final_violation_count == 0

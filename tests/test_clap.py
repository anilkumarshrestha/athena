"""Clap the beats: one beat per akshara (Nepali) or syllable (English), counted in code."""

import random

from athena.clap import beats, round_words
from athena.presets import preset


def test_beats_are_what_children_clap():
    assert beats("ne", "सीता") == ["सी", "ता"]
    assert beats("ne", "बिरालो") == ["बि", "रा", "लो"]
    assert beats("ne", "घर") is None  # 2 aksharas but said "ghar": left out
    assert beats("en", "rabbit") == ["rab", "bit"]
    assert beats("en", "garden") == ["gar", "den"]
    assert beats("en", "jumped") == ["jumped"]  # -ed is not a beat after p
    assert beats("en", "elephant") == ["e", "le", "phant"]


def test_round_uses_only_readable_words():
    from athena.lexicon import decodable_words

    _, units = preset("ne_mid")
    words = round_words("ne", units, random.Random(1))
    readable = set(decodable_words("ne", units))
    assert 4 <= len(words) <= 6 and all(w["word"] in readable for w in words)
    assert all(len(w["beats"]) >= 1 for w in words)


def test_clap_api_counts_taps(own):
    from fastapi.testclient import TestClient

    import athena.api as api
    from athena.store import store

    learner = store.get_learner("ram")
    c = TestClient(api.app)
    own(c, learner)
    words = c.get(f"/api/learners/{learner.id}/clap/ne").json()
    w = words[0]
    right = c.post(f"/api/learners/{learner.id}/clap/ne", json={"word": w["word"], "taps": len(w["beats"])}).json()
    wrong = c.post(f"/api/learners/{learner.id}/clap/ne", json={"word": w["word"], "taps": len(w["beats"]) + 1}).json()
    assert right["correct"] and not wrong["correct"]
    assert c.get(f"/api/learners/{learner.id}/clap/ne/audio/notaword").status_code == 404  # no open voice service

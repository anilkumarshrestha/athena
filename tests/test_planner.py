"""Planner theme resolution: offline, no model calls."""

from athena.agents.planner import THEMES, _resolve, plan
from athena.presets import preset

GOAT = next(t for t in THEMES if "goat" in t.text)
KITE = next(t for t in THEMES if "kite" in t.text)


def test_unreadable_natural_word_swapped_for_readable_one():
    lang, m = preset("ne_mid")  # no conjuncts: बाख्रा (ख्र) is unreadable, खसी is fine
    ok, use, avoid = _resolve(GOAT, lang, m)
    assert ok and use == ["खसी"] and avoid == ["बाख्रा"]


def test_theme_with_no_readable_key_word_is_never_picked():
    lang, m = preset("ne_mid")  # चङ्गा needs ङ्ग
    assert not _resolve(KITE, lang, m)[0]
    assert all(plan(lang, m, "राम", seed=s).theme != KITE.text for s in range(40))

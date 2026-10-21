"""Reading stages and story personalisation (revisit words, no repeats, style per level). Offline."""

import athena.api as api
from athena.agents.planner import THEMES, plan
from athena.agents.writer import build_prompt
from athena.mastery import UnitState
from athena.presets import preset
from athena.progression import SEQUENCE
from athena.stages import NAMES, stage, threshold
from athena.store import store


def _units(lang: str, n: int) -> dict[str, UnitState]:
    return {sig: UnitState("mastered") for sig in SEQUENCE[lang][:n]}


def test_stage_thresholds_and_progress():
    for lang in ("ne", "en"):
        total = len(SEQUENCE[lang])
        assert stage(lang, {}).n == 1 and stage(lang, {}).total == total
        for i in range(1, len(NAMES)):
            at = threshold(i, total)
            assert stage(lang, _units(lang, at - 1)).n == i  # one short: still the stage before
            st = stage(lang, _units(lang, at))
            assert (st.n, st.name, st.start) == (i + 1, NAMES[i], at)
        last = stage(lang, _units(lang, total))
        assert last.n == 5 and last.next_at is None and last.next_name is None


def test_practising_units_do_not_count():
    units = {sig: UnitState("practicing") for sig in SEQUENCE["en"]}
    assert stage("en", units).mastered == 0


def test_learner_out_has_stage():
    out = api.learner_out(store.get_learner("sita"))
    assert set(out.stage) == set(out.level) and out.stage["ne"].name in NAMES


def test_recent_themes_are_skipped_unless_nothing_else_fits():
    lang, m = preset("ne_mid")
    first = plan(lang, m, "राम", seed=3).theme
    assert all(plan(lang, m, "राम", seed=s, recent=frozenset({first})).theme != first for s in range(20))
    everything = frozenset(t.text for t in THEMES)
    assert plan(lang, m, "राम", seed=3, recent=everything).theme  # falls back, never fails


def test_revisit_words_are_in_the_bank_and_the_prompt():
    lang, m = preset("ne_mid")
    p = plan(lang, m, "राम", seed=1, revisit_words=["खसी"], recent_titles=["खसी र हजुरबुबा"])
    assert "खसी" in p.word_bank
    prompt = build_prompt(p)
    assert "found hard recently" in prompt and "खसी र हजुरबुबा" in prompt
    plain = build_prompt(plan(lang, m, "राम", seed=1))
    assert "found hard recently" not in plain and "recent stories" not in plain


def test_style_grows_with_level():
    lang, m = preset("en_p2")
    one, three = (build_prompt(plan(lang, m, "Leo", seed=1, level=lv)) for lv in (1, 3))
    assert "level 1" in one and "repeated" in one
    assert "level 3" in three and "problem" in three

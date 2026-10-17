"""Progression: new-unit introduction, difficulty level, story shape limits. Offline."""

from athena.mastery import UnitState
from athena.progression import LEVELS, next_level, next_units, should_introduce, unlock_value
from athena.verifier.shape import check_shape


def known(*sigs):
    return frozenset(sigs)


# --- unlock value / next units --------------------------------------------------


def test_unlock_value_counts_new_readable_words():
    base = known("c:आ", "c:म", "m:ा")  # reads आमा, मामा
    assert unlock_value("ne", base, "c:ब") >= 1  # बाबा
    assert unlock_value("ne", base, "c:ब") > unlock_value("ne", base, "c:ञ")


def test_next_units_picks_high_value_from_teaching_window():
    units = {s: UnitState("mastered", 3, 3) for s in ("c:आ", "c:म", "m:ा", "c:क", "c:र")}
    picked = next_units("ne", units, k=2)
    assert len(picked) == 2
    assert all(p not in units for p in picked)


def test_next_units_english_follows_phonics_window():
    units = {f"g:{g}": UnitState("mastered", 3, 3) for g in "s a t p i n".split()}
    picked = next_units("en", units, k=1)
    assert picked and picked[0].startswith("g:")
    assert picked[0][2:] in "m d g o c k ck e u r h b f ff l ll ss".split()


# --- introduction rule --------------------------------------------------------------


def test_introduce_only_when_ready():
    calm = {"c:क": UnitState("mastered", 3, 3)}
    assert should_introduce(calm, [0.95, 0.92])
    assert not should_introduce(calm, [0.95, 0.70])  # last session weak
    assert not should_introduce(calm, [])  # no evidence yet
    busy = {"c:क": UnitState("practicing"), "c:ख": UnitState("practicing")}
    assert not should_introduce(busy, [1.0, 1.0])  # already practising two


# --- level ----------------------------------------------------------------------------


def test_level_moves_one_step_at_a_time():
    assert next_level(1, [0.95, 0.92]) == 2
    assert next_level(3, [0.95, 0.95]) == 3
    assert next_level(2, [0.95, 0.5]) == 1
    assert next_level(2, [0.8]) == 2


# --- story shape (enforced like letters) -----------------------------------------------


def test_long_word_is_a_shape_violation():
    lim = LEVELS[1]
    v = check_shape("ne", ["हजुरआमाहरू आउनुभयो।"], lim)
    assert v and "aksharas" in v[0].reason


def test_too_many_words_in_a_sentence():
    lim = LEVELS[1]
    v = check_shape("en", ["Sam sat in a pan and a pit and a tin."], lim)
    assert any("words" in x.reason for x in v)


def test_names_exempt_from_length():
    assert check_shape("en", ["Krishnamurthy sat."], LEVELS[1], frozenset({"krishnamurthy"})) == []

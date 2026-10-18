"""Placement diagnostic: tiers of cards, adult marks each read / not yet. Offline."""

from athena.diagnostic import diagnostic, place


def answer(lang, correct_tiers, partial=None, seed=1):
    """Pass every card in correct_tiers; in tier `partial` pass only the first card."""
    d = diagnostic(lang, seed=seed)
    responses = {}
    for t in d:
        if t.kind == "listen":
            continue
        if t.number in correct_tiers:
            responses |= {c.id: True for c in t.cards}
        elif t.number == partial:
            responses |= {c.id: i == 0 for i, c in enumerate(t.cards)}
            break
        else:
            responses |= {c.id: False for c in t.cards}
            break
    return d, responses


def test_cards_are_short_and_each_tests_units():
    for lang in ("ne", "en"):
        d = diagnostic(lang, seed=3)
        assert 15 <= sum(len(t.cards) for t in d) <= 32
        assert all(c.tests for t in d for c in t.cards)


def test_same_seed_same_cards():
    a = [c.text for t in diagnostic("ne", seed=5) for c in t.cards]
    b = [c.text for t in diagnostic("ne", seed=5) for c in t.cards]
    assert a == b


def test_beginner_who_knows_nothing():
    d, r = answer("ne", correct_tiers=set())
    p = place("ne", d, r)
    assert p.level == 1
    assert len(p.mastered) == 0
    assert p.practicing == ["c:क", "m:ा"]  # starter order: opens real words fastest


def test_passed_tier_masters_untested_units_too():
    d, r = answer("ne", correct_tiers={1})
    p = place("ne", d, r)
    assert {"c:क", "c:म", "c:आ"} <= p.mastered  # tier 1 inventory, tested or not
    assert p.level == 1


def test_partial_tier_masters_only_cards_read():
    d, r = answer("ne", correct_tiers={1}, partial=2)
    p = place("ne", d, r)
    t2 = next(t for t in d if t.number == 2)
    assert set(t2.cards[0].tests) <= p.mastered
    assert not set(t2.cards[1].tests) <= p.mastered


def test_strong_reader_reaches_level_three():
    d, r = answer("ne", correct_tiers={1, 2, 3, 4, 5})
    p = place("ne", d, r)
    assert p.level == 3
    assert any(u.startswith("k:") for u in p.mastered)


def test_english_tricky_words_scored_separately():
    d = diagnostic("en", seed=2)
    tricky = next(t for t in d if t.always and t.kind == "read")
    t1, t2 = (next(t for t in d if t.number == n) for n in (1, 2))
    r = {c.id: True for c in t1.cards} | {c.id: False for c in t2.cards} | {c.id: True for c in tricky.cards}
    p = place("en", d, r)
    assert all(f"w:{c.text.lower()}" in p.mastered for c in tricky.cards)
    assert {"g:s", "g:a", "g:t"} <= p.mastered


def test_near_beginner_practises_starter_units_not_one_letter_words():
    # Kiran (17 Oct): knew इ न स, was given म + ऊ (one-letter words) and got a "story" of म ऊ.
    from athena.diagnostic import Placement  # noqa: F401
    from athena.mastery import UnitState
    from athena.progression import next_units

    units = {u: UnitState("mastered") for u in ("c:इ", "c:न", "c:स")}
    assert next_units("ne", units, k=2) == ["c:क", "m:ा"]


def test_listen_tier_first_self_scored_and_prioritises_recognised_letters():
    d = diagnostic("ne", seed=4)
    listen = d[0]
    assert listen.kind == "listen" and len(listen.cards) == 4
    assert all(c.text in c.options and len(c.options) == 3 for c in listen.cards)
    # Recognised by sound but read nothing: start with a recognised letter
    r = {c.id: True for c in listen.cards} | {c.id: False for c in d[1].cards}
    p = place("ne", d, r)
    assert not p.mastered  # recognition is not mastery
    assert p.recognized == {u for c in listen.cards for u in c.tests}


def test_english_letters_are_said_as_in_class():
    from athena import tts

    assert tts.letter_phrase("en", "a") == "a for apple"
    assert tts.letter_phrase("en", "s") == "s for sun"
    assert tts.letter_phrase("en", "ck").startswith("ck, as in ")  # never starts a word
    assert tts.letter_phrase("ne", "ह").startswith("ह, ")

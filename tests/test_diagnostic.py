"""Placement diagnostic: tiers of cards, adult marks each read / not yet. Offline."""

from athena.diagnostic import diagnostic, place


def answer(lang, correct_tiers, partial=None, seed=1):
    """Pass every card in correct_tiers; in tier `partial` pass only the first card."""
    d = diagnostic(lang, seed=seed)
    responses = {}
    for t in d:
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
    assert p.practicing == ["c:अ", "c:आ"]  # start at the beginning


def test_passed_tier_masters_untested_units_too():
    d, r = answer("ne", correct_tiers={1})
    p = place("ne", d, r)
    assert {"c:क", "c:म", "c:आ"} <= p.mastered  # tier 1 inventory, tested or not
    assert p.level == 1


def test_partial_tier_masters_only_cards_read():
    d, r = answer("ne", correct_tiers={1}, partial=2)
    p = place("ne", d, r)
    first = d[1].cards[0]
    assert set(first.tests) <= p.mastered
    assert not set(d[1].cards[1].tests) <= p.mastered


def test_strong_reader_reaches_level_three():
    d, r = answer("ne", correct_tiers={1, 2, 3, 4, 5})
    p = place("ne", d, r)
    assert p.level == 3
    assert any(u.startswith("k:") for u in p.mastered)


def test_english_tricky_words_scored_separately():
    d = diagnostic("en", seed=2)
    tricky = next(t for t in d if t.always)
    r = {c.id: True for c in d[0].cards} | {c.id: False for c in d[1].cards} | {c.id: True for c in tricky.cards}
    p = place("en", d, r)
    assert all(f"w:{c.text.lower()}" in p.mastered for c in tricky.cards)
    assert {"g:s", "g:a", "g:t"} <= p.mastered

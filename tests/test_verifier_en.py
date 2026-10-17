"""English verifier tests. Closed vocabulary: a word must be in the lexicon.

Mastery signatures:
  g:<grapheme>   g:sh, g:a_e   (split digraph; its trailing "_e" marker is not a unit)
  w:<word>       tricky word explicitly taught, w:said
"""

import json
from pathlib import Path

import pytest

from athena.verifier.english import (
    GRAPHEME_PHASE,
    EnglishVerifier,
    LexEntry,
    load_lexicon,
    spell,
)

LEX = {
    "sat": LexEntry(("s", "a", "t"), False),
    "pin": LexEntry(("p", "i", "n"), False),
    "ship": LexEntry(("sh", "i", "p"), False),
    "cake": LexEntry(("c", "a_e", "k", "_e"), False),
    "cats": LexEntry(("c", "a", "t", "s"), False),
    "said": LexEntry(None, True),
    "the": LexEntry(None, True),
    "like": LexEntry(("l", "i_e", "k", "_e"), True),
}

BASIC = {"g:s", "g:a", "g:t", "g:p", "g:i", "g:n"}


def v(*sigs, allowed=()):
    return EnglishVerifier(frozenset(sigs), LEX, frozenset(allowed))


# --- spelling reconstruction ---------------------------------------------------


def test_spell_plain():
    assert spell(("sh", "i", "p")) == "ship"


def test_spell_split_digraph():
    assert spell(("c", "a_e", "k", "_e")) == "cake"
    assert spell(("c", "a_e", "k", "_e", "s")) == "cakes"


# --- verify --------------------------------------------------------------------


def test_decodable_ok():
    r = v(*BASIC).verify("Sat pin. Pin sat!")
    assert r.ok
    assert r.words_checked == 4
    assert r.units_used == {"g:s", "g:a", "g:t", "g:p", "g:i", "g:n"}


def test_missing_grapheme():
    r = v(*BASIC).verify("ship")
    assert [x.unit for x in r.violations] == ["g:sh"]


def test_split_digraph_signature_has_no_marker():
    r = v("g:c", "g:a_e", "g:k").verify("cake")
    assert r.ok
    assert r.units_used == {"g:c", "g:a_e", "g:k"}


def test_short_a_does_not_unlock_split_digraph():
    r = v("g:c", "g:a", "g:k").verify("cake")
    assert [x.unit for x in r.violations] == ["g:a_e"]


def test_unknown_word_is_violation_never_guessed():
    r = v(*BASIC).verify("pat")  # decodable, but not in lexicon
    assert not r.ok
    assert r.violations[0].unit is None
    assert "lexicon" in r.violations[0].reason


def test_tricky_word_needs_explicit_teaching():
    assert not v(*BASIC).verify("said").ok
    assert v(*BASIC, "w:said").verify("said").ok
    r = v(*BASIC).verify("the")
    assert [x.unit for x in r.violations] == ["w:the"]


def test_tricky_word_decodable_once_graphemes_known():
    assert v("g:l", "g:i_e", "g:k").verify("like").ok
    assert v("w:like").verify("like").ok
    r = v("g:l").verify("like")
    assert [x.unit for x in r.violations] == ["w:like"]


def test_case_insensitive():
    assert v(*BASIC, "w:the").verify("The sat.").ok


def test_allowed_words_for_names():
    r = v(*BASIC, allowed=["sita"]).verify("Sita sat.")
    assert r.ok
    assert "sita" not in str(r.units_used)


def test_possessive_name_allowed():
    assert v(*BASIC, allowed=["sita"]).verify("Sita's pin.").ok


def test_contraction_rejected():
    assert not v(*BASIC).verify("it's").ok


def test_word_index():
    r = v(*BASIC).verify("sat sat ship")
    assert [(x.word_index, x.word) for x in r.violations] == [(2, "ship")]


def test_empty():
    r = v(*BASIC).verify(" ... ")
    assert r.ok and r.words_checked == 0


# --- real data integrity -------------------------------------------------------

DATA = Path(__file__).resolve().parent.parent / "data" / "en_lexicon.json"


@pytest.fixture(scope="module")
def lexicon():
    return load_lexicon(DATA)


def test_lexicon_size(lexicon):
    assert len(lexicon) >= 800


def test_lexicon_entries_reconstruct_and_use_known_graphemes(lexicon):
    for word, e in lexicon.items():
        if e.graphemes is None:
            assert e.is_tricky, word
            continue
        assert spell(e.graphemes) == word, word
        for g in e.graphemes:
            assert g == "_e" or g in GRAPHEME_PHASE, (word, g)


def test_split_digraph_markers_paired(lexicon):
    for word, e in lexicon.items():
        gs = e.graphemes or ()
        assert sum(g.endswith("_e") and g != "_e" for g in gs) == gs.count("_e"), word


def test_lexicon_json_is_sorted_and_unique():
    raw = json.loads(DATA.read_text(encoding="utf-8"))
    words = [e["word"] for e in raw]
    assert words == sorted(set(words))

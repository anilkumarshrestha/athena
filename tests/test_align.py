"""Reading assessment: align what was heard to the reference text. Offline."""

from athena.assess.align import assess

NE = "आमा र बिरालो घरमा छन्। बिरालो दूध पिउँछ।"


def outcomes(r):
    return [(w.expected, w.outcome) for w in r.words]


def test_perfect_read():
    r = assess("ne", NE, "आमा र बिरालो घरमा छन् बिरालो दूध पिउँछ", duration_s=30)
    assert all(w.outcome == "correct" for w in r.words)
    assert r.insertions == []
    assert r.words_correct == 8
    assert r.wcpm == 16.0


def test_punctuation_and_normalization_ignored():
    r = assess("ne", NE, "आमा, र बिरालो। घरमा छन्! बिरालो दूध पिउँछ", duration_s=60)
    assert r.words_correct == 8


def test_omission():
    r = assess("ne", NE, "आमा र घरमा छन् बिरालो दूध पिउँछ", duration_s=60)
    assert outcomes(r)[2] == ("बिरालो", "omitted")
    assert r.words[2].heard is None


def test_substitution_names_the_unit_that_went_wrong():
    # long ू read as short ु
    r = assess("ne", NE, "आमा र बिरालो घरमा छन् बिरालो दुध पिउँछ", duration_s=60)
    w = r.words[6]
    assert (w.expected, w.outcome, w.heard) == ("दूध", "substituted", "दुध")
    assert w.error_units == ["m:ू"]


def test_dropped_chandrabindu():
    r = assess("ne", NE, "आमा र बिरालो घरमा छन् बिरालो दूध पिउछ", duration_s=60)
    assert r.words[7].outcome == "substituted"
    assert r.words[7].error_units == ["m:ँ"]


def test_insertion():
    r = assess("ne", NE, "आमा र सानो बिरालो घरमा छन् बिरालो दूध पिउँछ", duration_s=60)
    assert all(w.outcome == "correct" for w in r.words)
    assert [(i.word, i.before_index) for i in r.insertions] == [("सानो", 2)]


def test_self_correction():
    # wrong attempt immediately followed by the right word
    r = assess("ne", NE, "आमा र बिरालो घरमा छन् बिरालो दुध दूध पिउँछ", duration_s=60)
    assert r.words[6].outcome == "self_corrected"
    assert r.insertions == []
    assert r.words_correct == 8  # self-corrections count as correct


def test_repetition_is_not_an_error():
    r = assess("ne", NE, "आमा आमा र बिरालो घरमा छन् बिरालो दूध पिउँछ", duration_s=60)
    assert all(w.outcome == "correct" for w in r.words)
    assert r.insertions == []


def test_empty_hypothesis_all_omitted():
    r = assess("ne", NE, "", duration_s=10)
    assert all(w.outcome == "omitted" for w in r.words)
    assert r.wcpm == 0.0


def test_unit_tally():
    r = assess("ne", NE, "आमा र बिरालो घरमा छन् बिरालो दुध पिउँछ", duration_s=60)
    assert r.unit_errors == {"m:ू": 1}
    assert r.unit_correct["c:ब"] == 2  # बिरालो read correctly twice


# --- English -------------------------------------------------------------------

EN = "Sam sat in a ship."


def test_english_substitution_grapheme():
    r = assess("en", EN, "sam sat in a sip", duration_s=60, allowed_words=frozenset({"sam"}))
    w = r.words[4]
    assert (w.expected, w.outcome) == ("ship", "substituted")
    assert w.error_units == ["g:sh"]


def test_english_tricky_word_error_unit():
    r = assess("en", "The cat sat.", "a cat sat", duration_s=60)
    assert r.words[0].outcome == "substituted"
    assert r.words[0].error_units == ["w:the"]

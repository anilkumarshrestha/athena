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
    # aspiration dropped: घ read as ग (audible, a common beginner error)
    r = assess("ne", NE, "आमा र बिरालो गरमा छन् बिरालो दूध पिउँछ", duration_s=60)
    w = r.words[3]
    assert (w.expected, w.outcome, w.heard) == ("घरमा", "substituted", "गरमा")
    assert w.error_units == ["c:घ"]


def test_vowel_length_is_not_audible_so_not_an_error():
    # दूध and दुध sound the same in Nepali; STT may write either
    r = assess("ne", NE, "आमा र बिरालो घरमा छन् बिरालो दुध पिउँछ", duration_s=60)
    assert all(w.outcome == "correct" for w in r.words)


def test_nasal_marks_are_not_scored():
    # STT drops ँ on correct reads; never blame the child for it
    r = assess("ne", NE, "आमा र बिरालो घरमा छन् बिरालो दूध पिउछ", duration_s=60)
    assert r.words[7].outcome == "correct"
    assert "m:ँ" not in r.unit_correct and "m:ँ" not in r.unit_errors


def test_sibilants_merge():
    r = assess("ne", "शिक्षक आए।", "सिक्सक आए", duration_s=60)
    assert r.words[0].outcome == "correct"


def test_split_word_glued_back():
    r = assess("ne", "आमा हाँस्नुहुन्छ।", "आमा हास्नु हुन्छ", duration_s=60)
    assert all(w.outcome == "correct" for w in r.words)
    assert r.insertions == []


def test_insertion():
    r = assess("ne", NE, "आमा र सानो बिरालो घरमा छन् बिरालो दूध पिउँछ", duration_s=60)
    assert all(w.outcome == "correct" for w in r.words)
    assert [(i.word, i.before_index) for i in r.insertions] == [("सानो", 2)]


def test_self_correction():
    # wrong attempt immediately followed by the right word
    r = assess("ne", NE, "आमा र बिरालो गरमा घरमा छन् बिरालो दूध पिउँछ", duration_s=60)
    assert r.words[3].outcome == "self_corrected"
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
    r = assess("ne", NE, "आमा र बिरालो गरमा छन् बिरालो दूध पिउँछ", duration_s=60)
    assert r.unit_errors == {"c:घ": 1}
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


# --- word parts for re-teaching ---------------------------------------------------

from athena.assess.parts import word_parts  # noqa: E402


def test_nepali_parts_are_aksharas():
    parts = word_parts("ne", "घरमा")
    assert [p.text for p in parts] == ["घ", "र", "मा"]
    assert parts[0].units == ("c:घ",)


def test_english_parts_are_graphemes_with_split_digraph():
    assert [p.text for p in word_parts("en", "ship")] == ["sh", "i", "p"]
    assert [p.text for p in word_parts("en", "cake")] == ["c", "a…e", "k"]
    assert [p.units for p in word_parts("en", "the")] == [("w:the",)]


def test_long_recording_split_at_quiet_points():
    import array

    from athena.assess.stt import PCM_RATE, SYNC_LIMIT_S, _split_quiet

    # 120 s of "speech" (loud) with a silent 300 ms gap at 47 s and 95 s
    s = array.array("h", [3000] * (120 * PCM_RATE))
    for gap in (47, 95):
        for i in range(gap * PCM_RATE, gap * PCM_RATE + 3 * PCM_RATE // 10):
            s[i] = 0
    chunks = _split_quiet(s.tobytes())
    lens = [len(c) // 2 / PCM_RATE for c in chunks]
    assert len(chunks) == 3 and all(x <= SYNC_LIMIT_S for x in lens)
    assert abs(lens[0] - 47) < 0.2  # cut inside the silence, not mid-word
    assert sum(len(c) for c in chunks) == len(s) * 2  # nothing lost


def test_hesitant_right_words_give_no_mastery_credit():
    from athena.assess.align import assess, discount_hesitant

    a = assess("ne", "घर घर", "घर घर", 4.0)
    before = dict(a.unit_correct)
    discount_hesitant("ne", a, {1})  # stopped long on the second घर
    assert {u: before[u] - 1 for u in before} == {u: a.unit_correct.get(u, 0) for u in before}
    discount_hesitant("ne", a, {0})  # and on the first: no credit left for घ this session
    assert "c:घ" not in a.unit_correct and a.words_correct == 2  # still read right: not an error

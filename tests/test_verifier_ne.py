"""Nepali decomposer + verifier tests. Written before the implementation.

Mastery model: a flat set of signatures.
  c:<x>  consonant or independent vowel   (c:क, c:आ)
  m:<x>  matra, modifier, or halanta      (m:ि, m:ं, m:्)
  k:<x>  conjunct, mastered as a whole    (k:क्ष)
"""

import pytest

from athena.verifier.nepali import (
    DecomposeError,
    NepaliVerifier,
    decompose,
    normalize,
)


def texts(word):
    return [u.text for u in decompose(word)]


# --- decompose ---------------------------------------------------------------


def test_plain_consonants():
    units = decompose("कमल")
    assert [u.base for u in units] == ["क", "म", "ल"]
    assert all(u.kind == "consonant" and u.matra is None for u in units)


def test_matras():
    units = decompose("किताब")
    assert texts("किताब") == ["कि", "ता", "ब"]
    assert [u.matra for u in units] == ["ि", "ा", None]


def test_independent_vowel():
    units = decompose("आमा")
    assert units[0].kind == "vowel" and units[0].base == "आ"
    assert units[1].base == "म" and units[1].matra == "ा"


def test_conjunct_ksha():
    units = decompose("क्षमा")
    assert texts("क्षमा") == ["क्ष", "मा"]
    assert units[0].kind == "conjunct"
    assert units[0].base == "क्ष"
    assert units[0].conjunct_parts == ("क", "ष")


def test_conjunct_with_matra():
    units = decompose("विद्यालय")
    assert texts("विद्यालय") == ["वि", "द्या", "ल", "य"]
    assert units[1].conjunct_parts == ("द", "य")
    assert units[1].matra == "ा"


def test_reph_is_conjunct():
    units = decompose("गर्मी")
    assert texts("गर्मी") == ["ग", "र्मी"]
    assert units[1].conjunct_parts == ("र", "म")
    assert units[1].matra == "ी"


def test_triple_conjunct():
    (unit,) = decompose("स्त्री")
    assert unit.conjunct_parts == ("स", "त", "र")
    assert unit.matra == "ी"


def test_anusvara():
    units = decompose("रंग")
    assert units[0].modifiers == ("ं",)


def test_chandrabindu_on_vowel():
    units = decompose("आँप")
    assert units[0].kind == "vowel"
    assert units[0].modifiers == ("ँ",)


def test_visarga_after_matra():
    units = decompose("दुःख")
    assert units[0].matra == "ु"
    assert units[0].modifiers == ("ः",)


def test_final_halanta():
    units = decompose("गर्नुहोस्")
    assert texts("गर्नुहोस्") == ["ग", "र्नु", "हो", "स्"]
    assert units[-1].has_halanta
    assert units[-1].kind == "consonant"
    assert not any(u.has_halanta for u in units[:-1])


def test_nukta_precomposed_equals_decomposed():
    # U+0958 is a composition exclusion: NFC turns it into क + ़
    assert normalize("क़") == "क़"
    (unit,) = decompose("क़")
    assert unit.base == "क़"


def test_zwj_zwnj_stripped():
    assert texts("क्‍ष") == texts("क्ष")
    assert texts("क्‌ष") == texts("क्ष")


def test_malformed_leading_matra():
    with pytest.raises(DecomposeError):
        decompose("िक")


def test_malformed_double_matra():
    with pytest.raises(DecomposeError):
        decompose("काि")


def test_non_devanagari_rejected():
    with pytest.raises(DecomposeError):
        decompose("कab")


# --- signatures ----------------------------------------------------------------


def test_signatures_consonant_matra():
    (unit,) = decompose("कि")
    assert unit.signatures() == {"c:क", "m:ि"}


def test_signatures_conjunct_does_not_require_parts():
    (unit,) = decompose("क्षा")
    assert unit.signatures() == {"k:क्ष", "m:ा"}


def test_signatures_halanta_and_modifiers():
    (unit,) = decompose("स्")
    assert unit.signatures() == {"c:स", "m:्"}
    (unit,) = decompose("कं")
    assert unit.signatures() == {"c:क", "m:ं"}


def test_signatures_vowel():
    (unit,) = decompose("आँ")
    assert unit.signatures() == {"c:आ", "m:ँ"}


# --- verifier ------------------------------------------------------------------


def v(*sigs):
    return NepaliVerifier(frozenset(sigs))


def test_verify_ok():
    result = v("c:क", "c:म", "c:ल").verify("कमल")
    assert result.ok
    assert result.violations == ()
    assert result.words_checked == 1
    assert result.units_used == {"c:क", "c:म", "c:ल"}


def test_verify_missing_matra():
    result = v("c:क", "c:त", "c:ब", "m:ा").verify("किताब")
    assert not result.ok
    assert [x.unit for x in result.violations] == ["m:ि"]
    assert result.violations[0].word == "किताब"
    assert result.violations[0].word_index == 0


def test_conjunct_not_mastered_from_parts():
    # knows क and ष separately, but not क्ष as a whole
    result = v("c:क", "c:ष", "c:म", "m:ा").verify("क्षमा")
    assert not result.ok
    assert [x.unit for x in result.violations] == ["k:क्ष"]


def test_conjunct_mastered_whole():
    assert v("k:क्ष", "c:म", "m:ा").verify("क्षमा").ok


def test_punctuation_and_multiple_words():
    result = v("c:क", "c:म", "c:ल").verify("कमल। कमल, कमल?")
    assert result.ok
    assert result.words_checked == 3


def test_word_index_counts_across_sentence():
    result = v("c:क", "c:म", "c:ल").verify("कमल कमल किल")
    assert [(x.word_index, x.unit) for x in result.violations] == [(2, "m:ि")]


def test_violation_reported_once_per_unit_per_word():
    result = v("c:क").verify("किकि")
    assert [x.unit for x in result.violations] == ["m:ि"]


def test_malformed_word_is_violation():
    result = v("c:क").verify("क cat")
    assert not result.ok
    assert result.violations[0].word == "cat"
    assert result.violations[0].unit is None
    assert "unexpected" in result.violations[0].reason


def test_devanagari_digit_is_violation():
    assert not v("c:क").verify("क ५").ok


def test_empty_text():
    result = v("c:क").verify("  । ")
    assert result.ok
    assert result.words_checked == 0

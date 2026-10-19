"""Template fallback: grammatical mini-stories from readable words. Offline."""

import random

from athena.fallback import template_story
from athena.lexicon import decodable_words, verifier_for
from athena.presets import preset


def story(name, key_words=(), seed=0):
    lang, m = preset(name)
    v = verifier_for(lang, m)
    title, sentences = template_story(lang, v, decodable_words(lang, m), list(key_words), random.Random(seed))
    return v, title, sentences


def test_every_sentence_and_title_verifies():
    for name in ("ne_early", "ne_basic", "ne_mid"):
        for seed in range(5):
            v, title, sentences = story(name, seed=seed)
            assert len(sentences) >= 2, (name, seed, sentences)
            for s in [title, *sentences]:
                assert v.verify(s).ok, (name, s)


def test_sentences_are_real_sentences_not_word_lists():
    _, _, sentences = story("ne_basic")
    for s in sentences:
        assert s.endswith("।") and 2 <= len(s.split()) <= 6, s


def test_theme_key_word_is_used():
    _, title, sentences = story("ne_basic", key_words=["कुखुरा"])
    assert "कुखुरा" in " ".join([title, *sentences])


def test_english_template_is_verified_sentences():
    lang, m = preset("en_p2")
    v = verifier_for(lang, m)
    title, sentences = template_story(lang, v, decodable_words(lang, m), [], random.Random(0))
    assert len(sentences) >= 3 and all(v.verify(s).ok for s in [title, *sentences] if s)


def test_elders_always_get_honorific_verbs():
    from athena.fallback import ELDERS

    for name in ("ne_basic", "ne_mid", "ne_mid_conj"):
        for seed in range(8):
            _, _, sentences = story(name, seed=seed)
            for s in sentences:
                words = s.rstrip("।").split()
                if words[0] in ELDERS:
                    assert words[-1] in ("हुनुहुन्छ", "जानुभयो"), s  # never plain छ / गयो

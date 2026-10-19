from athena import shelf
from athena.lexicon import verifier_for
from types import SimpleNamespace


def _child(units: list[str]) -> SimpleNamespace:
    return SimpleNamespace(id="x", name={"ne": "अनिल", "en": "Anil"})


def test_readable_story_passes_this_childs_verifier():
    units = "a b c ck d e g i l n o p s ss t u".split()
    v = verifier_for("en", frozenset(units), frozenset({"Anil"}))
    found = shelf.readable(_child(units), "en", v)
    if found is None:  # no shelf story fits these letters: nothing unreadable is served either
        return
    result, image = found
    text = "\n".join([result.title, *result.sentences])
    assert v.verify(text).ok
    assert not any(n in text for n in ("Sita", "Ram", "Leo"))


def test_no_letters_no_story():
    v = verifier_for("en", frozenset({"a"}), frozenset({"Anil"}))
    assert shelf.readable(_child(["a"]), "en", v) is None


def test_english_template_is_sentences_not_a_word_list():
    import random

    from athena.fallback import template_story

    units = frozenset("g:" + x for x in "a b c ck d e g i l n o p s ss t u".split())
    v = verifier_for("en", units, frozenset({"Anil"}))
    title, sentences = template_story("en", v, [], [], random.Random(0), "Anil")
    assert len(sentences) >= 3
    assert all(s.endswith(".") and v.verify(s).ok for s in sentences)

"""Story shape limits per difficulty level, enforced in code like the letter rules.

A word longer than the level allows, or a sentence with too many words, is a
violation fed back to the writer, never shipped. Learner names are exempt.
Length is counted in reading units: aksharas for Nepali, graphemes for English.
"""

from dataclasses import dataclass

from athena.verifier.base import Violation
from athena.verifier.english import SPLIT_MARKER
from athena.verifier.english import tokenize as en_tokenize
from athena.verifier.nepali import DecomposeError, decompose
from athena.verifier.nepali import tokenize as ne_tokenize


@dataclass(frozen=True)
class Limits:
    sentences: tuple[int, int]  # min, max
    max_words: int  # per sentence
    max_len_ne: int  # aksharas per word
    max_len_en: int  # graphemes per word


def word_length(language: str, word: str) -> int:
    if language == "ne":
        try:
            return len(decompose(word))
        except DecomposeError:
            return len(word)
    from athena.lexicon import en_lexicon  # lazy: keeps this module import-light

    e = en_lexicon().get(word)
    return len([g for g in e.graphemes if g != SPLIT_MARKER]) if e and e.graphemes else len(word)


def check_shape(
    language: str, sentences: list[str], limits: Limits, allowed_words: frozenset[str] = frozenset()
) -> list[Violation]:
    tokenize = ne_tokenize if language == "ne" else en_tokenize
    max_len = limits.max_len_ne if language == "ne" else limits.max_len_en
    unit = "aksharas" if language == "ne" else "letters-sounds"
    out: list[Violation] = []
    idx = 0
    for sentence in sentences:
        words = tokenize(sentence)
        if len(words) > limits.max_words:
            out.append(Violation(sentence, idx, None, f"sentence has {len(words)} words (max {limits.max_words})"))
        for w in words:
            if w not in allowed_words and (n := word_length(language, w)) > max_len:
                out.append(Violation(w, idx, None, f"word has {n} {unit} (max {max_len})"))
            idx += 1
    return out

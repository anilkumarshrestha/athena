"""Break a word into the parts a child reads, for re-teaching ("see its parts").

Nepali: aksharas from the decomposer (घ र मा). English: graphemes from the lexicon,
with a split digraph shown at the vowel as "a…e". Each part carries its mastery
signatures, so the parts behind this child's error can be highlighted.
Pure code: no model decides how a word is split.
"""

from dataclasses import dataclass

from athena.lexicon import en_lexicon
from athena.verifier.english import SPLIT_MARKER
from athena.verifier.nepali import DecomposeError, decompose


@dataclass(frozen=True)
class Part:
    text: str
    units: tuple[str, ...]


def word_parts(language: str, word: str) -> list[Part]:
    if language == "ne":
        try:
            return [Part(u.text, tuple(sorted(u.signatures()))) for u in decompose(word)]
        except DecomposeError:
            return [Part(word, ())]
    entry = en_lexicon().get(word.lower())
    if not entry or not entry.graphemes:
        return [Part(word, (f"w:{word.lower()}",) if entry else ())]  # tricky or unknown: whole word
    parts = []
    for g in entry.graphemes:
        if g == SPLIT_MARKER:
            continue  # the silent e is shown with its vowel
        text = f"{g[0]}…e" if g.endswith(SPLIT_MARKER) else g
        parts.append(Part(text, (f"g:{g}",)))
    return parts

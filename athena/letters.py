"""Letter mode: for children who can read too few words for any real story.

Below MIN_STORY_WORDS readable words, a "story" can only be the same two words shuffled
(Kiran, 17 Oct: "म ऊ किरण।"). So no story is generated: the child gets letter cards
instead. Each card shows a letter they are learning or know, with an example word
to hear (a familiar noun, for listening, not for reading). No model call to build it.
"""

from functools import lru_cache

from athena.agents.picture import EN_NOUNS
from athena.lexicon import ne_seed
from athena.mastery import UnitState, practice_targets

MIN_STORY_WORDS = 15
MAX_CARDS = 6
_NOUN_CATEGORIES = {"animals", "food", "objects", "family", "body", "nature", "places"}


@lru_cache
def _ne_examples() -> list[tuple[str, frozenset[str]]]:
    rows = [(e["word"], frozenset(e["signatures"])) for e in ne_seed() if e["category"] in _NOUN_CATEGORIES]
    return sorted(rows, key=lambda r: len(r[0]))  # short words first


def example_word(language: str, unit: str) -> str | None:
    glyph = unit.split(":", 1)[1]
    if language == "ne":
        # A consonant or vowel should start the word; a vowel sign just needs to be in it.
        for word, sigs in _ne_examples():
            if unit in sigs and (unit.startswith("m:") or word.startswith(glyph)):
                return word
        # No example noun (ऊ): say the letter itself; a vowel sign is said on क (कू).
        return f"क{glyph}" if unit.startswith("m:") else glyph
    if unit.startswith("w:"):
        return glyph
    # shortest first, then alphabetical: the same word on every run (sets have no order)
    starts = sorted((n for n in EN_NOUNS if n.startswith(glyph)), key=lambda n: (len(n), n))
    inside = sorted((n for n in EN_NOUNS if glyph in n), key=lambda n: (len(n), n))
    return (starts or inside or [glyph])[0]


def letter_cards(language: str, units: dict[str, UnitState]) -> list[dict]:
    """Practising letters first, then known ones; each with an example word to hear."""
    practising = practice_targets(units)
    known = [s for s, u in units.items() if u.state == "mastered"]
    cards = []
    for unit in [*practising, *known]:
        ex = example_word(language, unit)
        if ex:
            cards.append({"unit": unit, "example": ex, "practising": unit in practising})
        if len(cards) == MAX_CARDS:
            break
    return cards

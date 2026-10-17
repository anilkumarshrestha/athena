"""Progression: which units to teach next, and how hard stories should be. Pure code.

New units. When a learner is practising fewer than 2 units and read the last two
stories with >= 90% accuracy, introduce up to 2 unseen units. Which ones: among the
next few units of the familiar teaching order (varnamala / phonics phases) that
unlock at least one new word, the ones that make the most new words readable
("unlock value"). Units that unlock nothing yet are skipped until they do. So ु, न, भ, य come
early in Nepali: they unlock the honorific verbs every story about elders needs.

Level. Three bands of story shape (sentences, words per sentence, word length).
Up one level after two strong sessions (>= 90%), down one after a weak one (< 60%).
One step at a time, so a teacher can always say why.
"""

from functools import lru_cache

from athena.mastery import UnitState
from athena.verifier.english import _PHASES, grapheme_signatures
from athena.verifier.shape import Limits

# --- difficulty levels ----------------------------------------------------------------

# Nepali word length starts at 5 aksharas: honorific verbs for elders (आ·उ·नु·भ·यो) must be
# possible from level 1. Beginner readers use 3-6 words per sentence.
LEVELS: dict[int, Limits] = {
    1: Limits(sentences=(3, 3), max_words=5, max_len_ne=5, max_len_en=4),
    2: Limits(sentences=(3, 4), max_words=6, max_len_ne=6, max_len_en=5),
    3: Limits(sentences=(4, 5), max_words=8, max_len_ne=7, max_len_en=7),
}
UP_ACCURACY, DOWN_ACCURACY = 0.9, 0.6


def next_level(level: int, recent_accuracy: list[float]) -> int:
    if recent_accuracy and recent_accuracy[-1] < DOWN_ACCURACY:
        return max(1, level - 1)
    if len(recent_accuracy) >= 2 and min(recent_accuracy[-2:]) >= UP_ACCURACY:
        return min(max(LEVELS), level + 1)
    return level


# --- unit introduction --------------------------------------------------------------------

READY_ACCURACY = 0.9
MAX_PRACTICING = 2
WINDOW = 6  # how far ahead of the teaching order we may look

_NE_ORDER = (
    "अ आ इ ई उ ऊ ए ऐ ओ औ "
    "क ख ग घ ङ च छ ज झ ञ ट ठ ड ढ ण त थ द ध न प फ ब भ म य र ल व श ष स ह"
).split()
_NE_MATRAS = "ा ि ी ु ू े ै ो ौ ं ँ ्".split()
_NE_CONJ = "क्ष त्र ज्ञ न्छ स्त न्त र्म न्न ल्ल म्म र्न स्न क्त प्त".split()


def _ne_sequence() -> list[str]:
    """Varnamala order, with the matras taught alongside the first consonant rows."""
    cons = [f"c:{c}" for c in _NE_ORDER]
    matras = [f"m:{m}" for m in _NE_MATRAS]
    seq = cons[:10] + matras[:4] + cons[10:20] + matras[4:8] + cons[20:] + matras[8:]
    return seq + [f"k:{k}" for k in _NE_CONJ]


def _en_sequence() -> list[str]:
    return [f"g:{g}" for p in sorted(_PHASES) for g in _PHASES[p].split()]


SEQUENCE = {"ne": _ne_sequence(), "en": _en_sequence()}


@lru_cache
def _corpus(language: str) -> tuple[frozenset[str], ...]:
    """Each known word as the set of units it needs."""
    if language == "ne":
        from athena.lexicon import ne_seed

        return tuple(frozenset(e["signatures"]) for e in ne_seed())
    from athena.lexicon import en_lexicon

    return tuple(frozenset(grapheme_signatures(e.graphemes)) for e in en_lexicon().values() if e.graphemes)


def readable_count(language: str, known: frozenset[str]) -> int:
    return sum(need <= known for need in _corpus(language))


def unlock_value(language: str, known: frozenset[str], unit: str) -> int:
    return readable_count(language, known | {unit}) - readable_count(language, known)


def next_units(language: str, units: dict[str, UnitState], k: int = 2) -> list[str]:
    """Up to k unseen units: highest unlock value within the next WINDOW of the teaching order."""
    known = frozenset(s for s, u in units.items() if u.state in ("mastered", "practicing"))
    unseen = [s for s in SEQUENCE[language] if s not in units or units[s].state == "unseen"]
    picked: list[str] = []
    for _ in range(k):
        have = known | set(picked)
        options = [s for s in unseen if s not in picked]
        # Skip units that would not unlock any new word yet (ई, ऊ early on); look at the
        # next WINDOW of the teaching order that do, and take the most valuable.
        useful = [s for s in options if unlock_value(language, have, s) > 0][:WINDOW]
        if not useful:
            useful = options[:1]  # nothing unlocks anything: just follow the order
        if not useful:
            break
        # Ties keep teaching order (max is stable on the first maximum).
        picked.append(max(useful, key=lambda s: unlock_value(language, have, s)))
    return picked


def should_introduce(units: dict[str, UnitState], recent_accuracy: list[float]) -> bool:
    practicing = sum(u.state == "practicing" for u in units.values())
    return (
        practicing < MAX_PRACTICING
        and len(recent_accuracy) >= 2
        and min(recent_accuracy[-2:]) >= READY_ACCURACY
    )

"""Placement diagnostic: a short, playful card check that sets a new learner's start.

The child reads a big card aloud; the adult beside them taps "read it" or "not yet".
Adult judgement, not STT: faster (no 3 s round trip per card) and more reliable for
young children's speech. The child never sees "wrong", only the next card.

Tiers get harder; the check stops after the first tier the child finds hard.
  tier passed (>= 80%) -> every unit of the tier is mastered, tested or not, except
                          the units of cards missed (those become practising)
  tier failed           -> only units of cards read are mastered; stop
Level follows from how far the child got. Pure code; explainable to a parent.
"""

import random
from dataclasses import dataclass, field

from athena.verifier.english import _PHASES, grapheme_signatures
from athena.verifier.nepali import decompose

PASS = 0.8
MAX_PRACTICING = 2


@dataclass(frozen=True)
class Card:
    id: str
    text: str
    tests: tuple[str, ...]  # units the card checks


@dataclass(frozen=True)
class Tier:
    number: int
    name: str
    inventory: tuple[str, ...]  # units credited when the tier is passed
    cards: tuple[Card, ...]
    always: bool = False  # asked even after an earlier tier stops the check (tricky words)
    level_if_passed: int = 1


@dataclass
class Placement:
    mastered: set[str] = field(default_factory=set)
    practicing: list[str] = field(default_factory=list)
    level: int = 1
    reached_tier: int = 0


def _ne_units(word: str) -> tuple[str, ...]:
    out: list[str] = []
    for u in decompose(word):
        out.extend(s for s in sorted(u.signatures()) if s not in out)
    return tuple(out)


# --- Nepali ------------------------------------------------------------------------

_NE_T1 = "अ आ इ उ क ग म न प र ल स त द ब ह".split()
_NE_T2 = "ए ओ ई ऊ ख घ च छ ज झ ट ठ ड ढ थ ध फ भ य व श".split()
_NE_T3 = ["का", "कि", "की", "कु", "कू", "के", "कै", "को", "कौ", "कं", "माँ"]
_NE_T4 = ["आमा", "बाबा", "घर", "बिरालो", "कुकुर", "पानी", "दूध", "केरा", "खेत", "किताब", "हात", "रोटी"]
_NE_T5 = ["स्कुल", "हात्ती", "बच्चा", "खुट्टा", "सुन्तला", "झ्याल", "बाख्रा", "जुत्ता", "क्षमा", "पत्र"]


def _ne_tiers(rng: random.Random) -> list[Tier]:
    def cards(prefix: str, texts: list[str], n: int, tests) -> tuple[Card, ...]:
        pick = rng.sample(texts, min(n, len(texts)))
        return tuple(Card(f"{prefix}{i}", t, tests(t)) for i, t in enumerate(pick))

    letter = lambda t: (f"c:{t}",)  # noqa: E731
    matra = lambda t: tuple(s for s in _ne_units(t) if s.startswith("m:"))  # noqa: E731
    conj = lambda t: tuple(s for s in _ne_units(t) if s.startswith("k:"))  # noqa: E731
    t3_inv = tuple(sorted({s for t in _NE_T3 for s in matra(t)}))
    t5_inv = tuple(sorted({s for t in _NE_T5 for s in conj(t)}))
    return [
        Tier(1, "letters", tuple(f"c:{c}" for c in _NE_T1), cards("n1-", _NE_T1, 6, letter)),
        Tier(2, "more letters", tuple(f"c:{c}" for c in _NE_T2), cards("n2-", _NE_T2, 6, letter)),
        Tier(3, "vowel signs", t3_inv, cards("n3-", _NE_T3, 6, matra)),
        # Words use earlier units; passing them shows the child blends. They test their units.
        Tier(4, "words", (), cards("n4-", _NE_T4, 5, _ne_units), level_if_passed=2),
        Tier(5, "joined letters", t5_inv, cards("n5-", _NE_T5, 5, conj), level_if_passed=3),
    ]


# --- English -------------------------------------------------------------------------

_EN_SET1 = "s a t p i n".split()
_EN_SET2 = "m d g o c k ck e u r h b f l".split()
_EN_DIGRAPHS = "sh ch th ng ff ll ss".split()
_EN_CVC = ["cat", "dog", "sun", "pig", "bed", "hen", "cup", "map", "ship", "chip", "fish", "duck"]
_EN_TEAMS = ["rain", "boat", "feet", "moon", "car", "light", "fork", "cow", "coin"]
_EN_TRICKY = ["the", "said", "was", "you", "they", "to", "he", "she"]
_EN_P3_TEAMS = tuple(f"g:{g}" for g in "ai ee igh oa oo ar or ur ow oi ear air er".split())


def _en_tiers(rng: random.Random) -> list[Tier]:
    from athena.lexicon import en_lexicon

    lex = en_lexicon()

    def gtests(word: str) -> tuple[str, ...]:
        e = lex.get(word)
        return tuple(grapheme_signatures(e.graphemes)) if e and e.graphemes else ()

    def cards(prefix: str, texts: list[str], n: int, tests) -> tuple[Card, ...]:
        pick = rng.sample(texts, min(n, len(texts)))
        return tuple(Card(f"{prefix}{i}", t, tests(t)) for i, t in enumerate(pick))

    g = lambda t: (f"g:{t}",)  # noqa: E731
    return [
        Tier(1, "first sounds", tuple(f"g:{x}" for x in _EN_SET1), cards("e1-", _EN_SET1, 6, g)),
        Tier(2, "more sounds", tuple(f"g:{x}" for x in _EN_SET2), cards("e2-", _EN_SET2, 6, g)),
        Tier(3, "two letters, one sound", tuple(f"g:{x}" for x in _EN_DIGRAPHS), cards("e3-", _EN_DIGRAPHS, 5, g)),
        Tier(4, "short words", (), cards("e4-", _EN_CVC, 5, gtests), level_if_passed=2),
        Tier(5, "vowel teams", _EN_P3_TEAMS, cards("e5-", _EN_TEAMS, 5, gtests), level_if_passed=3),
        Tier(6, "tricky words", (), cards("e6-", _EN_TRICKY, 4, lambda t: (f"w:{t}",)), always=True),
    ]


def diagnostic(language: str, seed: int = 0) -> list[Tier]:
    rng = random.Random(seed)
    return _ne_tiers(rng) if language == "ne" else _en_tiers(rng)


def place(language: str, tiers: list[Tier], responses: dict[str, bool]) -> Placement:
    p = Placement()
    missed: list[str] = []
    stopped = False
    for tier in tiers:
        if stopped and not tier.always:
            continue
        asked = [c for c in tier.cards if c.id in responses]
        if not asked:
            if not tier.always:
                stopped = True
            continue
        read = [c for c in asked if responses[c.id]]
        for c in read:
            p.mastered.update(c.tests)
        missed_units = [u for c in asked if not responses[c.id] for u in c.tests if u not in p.mastered]
        if tier.always:
            continue
        if len(read) / len(asked) >= PASS:
            p.mastered.update(u for u in tier.inventory if u not in missed_units)
            p.reached_tier = tier.number
            p.level = max(p.level, tier.level_if_passed)
            missed.extend(missed_units)
        else:
            missed.extend(missed_units)
            stopped = True

    # Practise first what unlocks the most words: missed units, topped up from the
    # teaching order (a child with letters but no vowel signs gets ा, not another letter).
    from athena.mastery import UnitState
    from athena.progression import next_units, unlock_value

    known = frozenset(p.mastered)
    pool = [u for u in dict.fromkeys(missed) if u not in p.mastered]
    units = {u: UnitState("mastered") for u in p.mastered}
    pool += [u for u in next_units(language, units, k=MAX_PRACTICING) if u not in pool]
    if not pool:  # read nothing and nothing unlocks yet: start at the very beginning
        pool = list(tiers[0].inventory)
    value = {u: unlock_value(language, known, u) for u in pool}
    if not p.mastered or not any(value.values()):  # knows nothing yet: begin at the beginning (अ आ / s a)
        pool = [u for u in tiers[0].inventory if u not in p.mastered] or pool
    else:
        pool.sort(key=lambda u: value.get(u, 0), reverse=True)
    p.practicing = pool[:MAX_PRACTICING]
    return p

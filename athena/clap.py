"""Clap the beats: phonological awareness with rhythm. The child taps once per beat of a word.

A beat is what children clap in class:
  Nepali   one akshara (written syllable block): सी·ता, बि·रा·लो. Only words where every akshara
           is also a spoken beat: no conjuncts or virama, and the word ends in a vowel sign or a
           vowel (घर is said "ghar": 2 aksharas, 1 beat, so it is left out).
  English  one syllable, from the phonics lexicon's spelling units: a vowel unit starts a beat
           (rab·bit, gar·den); "-ed" is its own beat only after t or d (land·ed, but jumped).
Code counts the taps; nothing is judged by a model. Practice only: mastery does not change.
"""

import random

from athena.lexicon import decodable_words, en_lexicon
from athena.verifier.english import SPLIT_MARKER
from athena.verifier.nepali import DecomposeError, decompose

VOWELS = "aeiou"
ROUND = 6


def ne_beats(word: str) -> list[str] | None:
    try:
        aks = decompose(word)
    except DecomposeError:
        return None
    if not aks or "".join(a.text for a in aks) != word:
        return None
    if any(a.kind == "conjunct" or a.has_halanta for a in aks):
        return None
    last = aks[-1]
    if not (last.kind == "vowel" or last.matra):  # final inherent a is silent in speech
        return None
    return [a.text for a in aks]


def en_beats(word: str) -> list[str] | None:
    e = en_lexicon().get(word.lower())
    if not e or not e.graphemes:
        return None
    g = [x for x in e.graphemes if x != SPLIT_MARKER]
    if "".join(x.lstrip("_") for x in g) != word.lower():
        return None

    def vowel(i: int) -> bool:
        x = g[i]
        if x.startswith("_") or x[0] not in VOWELS:
            return False
        if x == "ed" and i == len(g) - 1:  # jumped: no beat; landed: a beat
            return i > 0 and g[i - 1][-1] in "td"
        return True

    vs = [i for i in range(len(g)) if vowel(i)]
    if not vs:
        return None
    # split each gap between two vowel units: one consonant unit goes right (ba·by), more: one each side
    cuts = []
    for a, b in zip(vs, vs[1:]):
        gap = b - a - 1
        if gap == 0:
            cuts.append(b)
        elif gap == 1:
            mid = g[a + 1]
            cuts.append(a + 1 if len(mid) == 1 or mid[0] != mid[-1] else -(a + 1))  # rabbit: rab·bit
        else:
            cuts.append(a + 2)
    parts, start = [], 0
    for c in cuts:
        if c < 0:  # a doubled letter shared out: "bb" -> b | b
            i = -c
            parts.append("".join(x.lstrip("_") for x in g[start:i]) + g[i][0])
            g_rest = g[i][1:]
            start = i + 1
            parts.append(None)  # placeholder joined below
            pending = g_rest
            continue
        piece = "".join(x.lstrip("_") for x in g[start:c])
        if parts and parts[-1] is None:
            parts[-1] = pending + piece
        else:
            parts.append(piece)
        start = c
    tail = "".join(x.lstrip("_") for x in g[start:])
    if parts and parts[-1] is None:
        parts[-1] = pending + tail
    else:
        parts.append(tail)
    return [p for p in parts if p]


def beats(language: str, word: str) -> list[str] | None:
    return ne_beats(word) if language == "ne" else en_beats(word)


def round_words(language: str, units: frozenset[str], rng: random.Random, n: int = ROUND) -> list[dict]:
    """n readable words with their beats, mostly 2-3 beats, one easy 1-beat word early."""
    pool: dict[int, list[tuple[str, list[str]]]] = {}
    for w in decodable_words(language, units):
        b = beats(language, w)
        if b and 1 <= len(b) <= 4:
            pool.setdefault(len(b), []).append((w, b))
    plan = [1, 2, 2, 3, 2, 3] if language == "ne" else [1, 2, 1, 2, 2, 3]
    out, used = [], set()
    for k in plan[:n]:
        options = [x for x in pool.get(k, []) if x[0] not in used] or \
            [x for kk in sorted(pool, key=lambda kk: abs(kk - k)) for x in pool[kk] if x[0] not in used]
        if not options:
            break
        w, b = rng.choice(options)
        used.add(w)
        out.append({"word": w, "beats": b})
    return out

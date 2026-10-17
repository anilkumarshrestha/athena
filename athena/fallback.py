"""Template fallback (PLAN §4): when no model draft passes, build a short, grammatical
story from words the child can read. No model call; every sentence is verified.

Slots use hand-picked word groups that make sense together (an animal can be small
or hungry, food can be hot or sweet), not raw seed categories, so the output never
says "the rice is blue". Sentences are anchored on the theme's key words so they
hang together. Nepali only: English has the closed lexicon and rarely falls back.
"""

import random

from athena.verifier.base import Verifier

ANIMALS = "बिरालो कुकुर गाई भैंसी बाख्रा खसी भेडा कुखुरा हाँस चरा मुसा घोडा बाँदर खरायो याक परेवा सुगा पुतली".split()
ANIMAL_ADJ = "सानो ठूलो कालो सेतो खैरो भोको खुसी".split()
FOOD = "भात दाल रोटी दूध दही मह चिया आलु केरा स्याउ आँप सुन्तला मकै साग".split()
FOOD_ADJ = "मीठो तातो चिसो अमिलो नरम".split()
FAMILY = "आमा बुबा बाबा दाइ दिदी भाइ बहिनी हजुरआमा हजुरबुबा काका काकी मामा".split()
OBJECTS = "किताब कापी कलम झोला लुगा टोपी थाल गिलास बल छाता घडी".split()
OBJ_ADJ = "रातो निलो हरियो सेतो कालो नयाँ सानो ठूलो राम्रो".split()
ANIMAL_PLACES = "घर आँगन बारी खेत बाटो गाउँ".split()
PEOPLE_PLACES = "घर स्कुल बजार खेत बारी आँगन कोठा भान्सा गाउँ".split()

# (pattern, slot groups). Slots fill left to right.
PATTERNS: list[tuple[str, list[list[str]]]] = [
    ("{}मा {} छ।", [ANIMAL_PLACES, ANIMALS]),
    ("{} {} छ।", [ANIMALS, ANIMAL_ADJ]),
    ("{} {} छ।", [FOOD, FOOD_ADJ]),
    ("{}को {} {} छ।", [FAMILY, OBJECTS, OBJ_ADJ]),
    ("यो {} हो।", [OBJECTS]),
    ("म {}मा छु।", [PEOPLE_PLACES]),
    ("यो {} हो।", [FOOD]),
]
MAX_SENTENCES = 4


def _fill(pattern: str, groups: list[list[str]], readable: set[str], focus: list[str], rng: random.Random,
          verifier: Verifier) -> str | None:
    """First verified filling, trying focus words first in each slot."""
    options = []
    for g in groups:
        words = [w for w in g if w in readable or w in focus]
        first = [w for w in focus if w in words]
        rest = [w for w in words if w not in first]
        rng.shuffle(rest)
        options.append(first + rest)
    if not all(options):
        return None
    # Small search: vary each slot over its first few options.
    for _ in range(12):
        s = pattern.format(*(o[0] if rng.random() < 0.6 else rng.choice(o[:4]) for o in options))
        if verifier.verify(s).ok:
            return s
    return None


def template_story(
    language: str, verifier: Verifier, readable_words: list[str], key_words: list[str], rng: random.Random
) -> tuple[str, list[str]]:
    """(title, sentences), all verified; ("", []) if nothing fits."""
    if language != "ne":
        return "", []
    readable = set(readable_words)
    focus = [w for w in key_words if w in readable] or []
    # Anchor on one animal and one family member so sentences share characters.
    for group in (ANIMALS, FAMILY):
        pool = [w for w in group if w in readable and w not in focus]
        if pool:
            focus.append(rng.choice(pool))

    sentences: list[str] = []
    patterns = PATTERNS[:]
    rng.shuffle(patterns)
    # Patterns that can use a focus word go first.
    patterns.sort(key=lambda p: not any(w in g for g in p[1] for w in focus))
    for pattern, groups in patterns:
        s = _fill(pattern, groups, readable, focus, rng, verifier)
        if s and s not in sentences:
            sentences.append(s)
        if len(sentences) == MAX_SENTENCES:
            break

    named = [w for w in focus if any(w in s for s in sentences)][:2]
    title = " र ".join(named) if len(named) == 2 else (named[0] if named else "")
    if title and not verifier.verify(title).ok:
        title = ""
    return title, sentences

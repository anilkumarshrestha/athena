"""Template fallback (PLAN §4): when no model draft passes, build a short, grammatical
story from words the child can read. No model call; every sentence is verified.

Grammatical is not enough: "मह तातो छ" (the honey is hot) and "आमाको बल" (mother's
ball) are correct but nobody says them (native review, 17 Oct). So slots are not
free cross-products: each noun lists only what is commonly said about it, and
possessions fit their owner (a brother's ball, a mother's umbrella). Edit the maps
below to tune; every sentence still goes through the verifier.

Sentences are anchored on the theme's key words so they hang together.
Nepali only: English has the closed lexicon and rarely falls back.
"""

import random

from athena.verifier.base import Verifier

# noun -> what is naturally said about it
ANIMAL_ADJ: dict[str, list[str]] = {
    "बिरालो": ["सानो", "कालो", "सेतो", "खैरो", "भोको"],
    "कुकुर": ["सानो", "ठूलो", "कालो", "सेतो", "खैरो", "भोको"],
    "गाई": ["ठूलो", "सेतो", "खैरो", "भोको"],
    "भैंसी": ["ठूलो", "कालो", "भोको"],
    "बाख्रा": ["सानो", "कालो", "सेतो", "भोको"],
    "खसी": ["सानो", "कालो", "सेतो", "भोको"],
    "भेडा": ["सानो", "सेतो"],
    "कुखुरा": ["सानो", "सेतो", "रातो", "भोको"],
    "हाँस": ["सेतो", "सानो"],
    "चरा": ["सानो"],
    "मुसा": ["सानो", "खैरो"],
    "घोडा": ["ठूलो", "कालो", "सेतो", "खैरो"],
    "खरायो": ["सानो", "सेतो"],
    "याक": ["ठूलो", "कालो"],
    "सुगा": ["हरियो", "सानो"],
}
FOOD_ADJ: dict[str, list[str]] = {
    "भात": ["तातो", "मीठो"],
    "दाल": ["तातो", "मीठो"],
    "रोटी": ["तातो", "मीठो", "नरम"],
    "दूध": ["तातो", "मीठो"],
    "दही": ["मीठो", "अमिलो"],
    "मह": ["मीठो"],
    "चिया": ["तातो", "मीठो"],
    "केरा": ["मीठो", "पहेंलो"],
    "स्याउ": ["मीठो", "रातो"],
    "आँप": ["मीठो", "पहेंलो"],
    "सुन्तला": ["मीठो", "अमिलो"],
    "कागती": ["अमिलो"],
    "साग": ["हरियो", "तातो"],
}
# owner -> things they naturally have
CHILDREN = "दाइ दिदी भाइ बहिनी".split()
ADULTS = "आमा बुबा बाबा हजुरआमा हजुरबुबा काका काकी मामा".split()
OWNS: dict[str, list[str]] = {
    **{c: ["बल", "किताब", "कापी", "कलम", "झोला", "टोपी"] for c in CHILDREN},
    **{a: ["छाता", "घडी", "झोला", "टोपी", "किताब"] for a in ADULTS},
}
OBJECT_ADJ: dict[str, list[str]] = {
    "बल": ["रातो", "निलो", "सानो", "नयाँ"],
    "किताब": ["नयाँ", "ठूलो", "राम्रो"],
    "कापी": ["नयाँ", "सानो"],
    "कलम": ["नयाँ", "निलो", "कालो"],
    "झोला": ["नयाँ", "रातो", "ठूलो"],
    "टोपी": ["नयाँ", "रातो", "कालो"],
    "छाता": ["कालो", "रातो", "ठूलो", "नयाँ"],
    "घडी": ["नयाँ", "राम्रो", "सानो"],
}
# Elders and older siblings take honorific verbs (आमा घरमा हुनुहुन्छ), never plain (आमा घरमा छ).
ELDERS = "आमा बुबा बाबा हजुरआमा हजुरबुबा काका काकी मामा दाइ दिदी".split()
ANIMAL_PLACES = "घर आँगन बारी खेत गाउँ".split()
PEOPLE_PLACES = "घर स्कुल बजार खेत बारी आँगन भान्सा गाउँ".split()


def _candidates() -> list[list[str]]:
    """Every natural sentence, grouped by pattern (one sentence per pattern per story)."""
    return [
        [f"{p}मा {a} छ।" for p in ANIMAL_PLACES for a in ANIMAL_ADJ],
        [f"{a} {adj} छ।" for a, adjs in ANIMAL_ADJ.items() for adj in adjs],
        [f"{f} {adj} छ।" for f, adjs in FOOD_ADJ.items() for adj in adjs],
        [f"{o}को {t} {adj} छ।" for o, things in OWNS.items() for t in things for adj in OBJECT_ADJ[t]],
        [f"यो {t} हो।" for t in OBJECT_ADJ],
        [f"यो {f} हो।" for f in FOOD_ADJ],
        [f"म {p}मा छु।" for p in PEOPLE_PLACES],
        [f"{e} {p}मा हुनुहुन्छ।" for e in ELDERS for p in PEOPLE_PLACES],
        [f"{e} {p} जानुभयो।" for e in ELDERS for p in ("बजार", "खेत", "बारी", "घर", "स्कुल")],
    ]


MAX_SENTENCES = 4


def template_story(
    language: str, verifier: Verifier, readable_words: list[str], key_words: list[str], rng: random.Random
) -> tuple[str, list[str]]:
    """(title, sentences), all verified; ("", []) if nothing fits."""
    if language != "ne":
        return "", []
    # Readability is the verifier's call, not seed-list membership (खसी is readable
    # for most learners but not in the seed list).
    def readable(w: str) -> bool:
        return w in readable_words or verifier.verify(w).ok

    focus = [w for w in key_words if readable(w)]
    # Anchor on one animal and one family member so sentences share characters.
    for pool in (list(ANIMAL_ADJ), CHILDREN + ADULTS):
        options = [w for w in pool if readable(w) and w not in focus]
        if options:
            focus.append(rng.choice(options))

    def score(s: str) -> int:
        return sum(w in s.split() or s.startswith(w) for w in focus)

    groups = []
    for group in _candidates():
        ok = [s for s in group if verifier.verify(s).ok]
        if ok:
            rng.shuffle(ok)
            ok.sort(key=score, reverse=True)  # focus words first, random among equals
            groups.append(ok)
    groups.sort(key=lambda g: score(g[0]), reverse=True)

    sentences = [g[0] for g in groups[:MAX_SENTENCES]]
    named = [w for w in focus if any(w in s for s in sentences)][:2]
    title = " र ".join(named) if len(named) == 2 else (named[0] if named else "")
    if title and not verifier.verify(title).ok:
        title = ""
    return title, sentences

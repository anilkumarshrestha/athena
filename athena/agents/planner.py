"""Planner: picks theme, focus units and the word bank the writer should draw from.

Deterministic (seeded RNG). No model call: the plan is cheap and must be explainable.

Themes carry their key nouns. Eval showed theme words were the main source of
Nepali violations (goat -> बाख्रा needs ख्र, kite -> चङ्गा needs ङ्ग), so the planner
only picks themes whose key things the child can read, and tells the writer which
spelling to use and which to avoid.
"""

import random
from dataclasses import dataclass, field

from athena.lexicon import decodable_words, verifier_for
from athena.models import Language, StoryPlan


@dataclass(frozen=True)
class Theme:
    text: str
    # Each group is one key thing in the theme, as alternative words (first = most natural).
    ne: list[list[str]] = field(default_factory=list)
    en: list[list[str]] = field(default_factory=list)


THEMES = [
    Theme("helping mother cook dal bhat in the kitchen", ne=[["आमा"], ["भात", "दाल"]], en=[["mum", "dad"], ["pot", "pan", "cook"]]),
    Theme("a goat that wanders off in the village", ne=[["बाख्रा", "खसी", "बोका"]], en=[["goat", "goats"]]),
    Theme("flying a kite on the rooftop during Dashain", ne=[["चङ्गा"]], en=[["kite", "kites"]]),
    Theme("a rainy day walk to school", ne=[["पानी", "झरी"], ["स्कुल", "बाटो"]], en=[["rain", "wet"]]),
    Theme("feeding the hens in the morning", ne=[["कुखुरा"]], en=[["hen", "hens"]]),
    Theme("a picnic by the river with family", ne=[["खोला", "नदी"]], en=[["picnic", "pond"]]),
    Theme("grandmother telling a story in the evening", ne=[["हजुरआमा"]]),
    Theme("planting maize in the field", ne=[["मकै"], ["खेत", "बारी"]], en=[["corn"], ["farm", "land"]]),
    Theme("a cat and a dog who become friends", ne=[["बिरालो"], ["कुकुर"]], en=[["cat", "cats"], ["dog", "dogs"]]),
    Theme("going to the market with father", ne=[["बजार", "पसल"], ["बुबा", "बाबा"]], en=[["dad"], ["shop", "shops"]]),
    Theme("seeing the mountains on a clear morning", ne=[["हिमाल", "पहाड", "डाँडा"]], en=[["hill", "hills"]]),
    Theme("a little bird building a nest", ne=[["चरा"]], en=[["nest", "nests"]]),
]
_BY_TEXT = {t.text: t for t in THEMES}

WORD_BANK_MAX = 150


def _resolve(theme: Theme, language: Language, mastery: frozenset[str]) -> tuple[bool, list[str], list[str]]:
    """(every key thing readable?, readable key words to use, natural words to avoid)."""
    v = verifier_for(language, mastery)
    use, avoid, ok = [], [], True
    for group in getattr(theme, language):
        readable = [w for w in group if v.verify(w).ok]
        if readable:
            use.append(readable[0])
            if readable[0] != group[0]:
                avoid.append(group[0])
        else:
            ok = False
            avoid.extend(group)
    return ok, use, avoid


def plan(
    language: Language,
    mastery: frozenset[str],
    learner_name: str,
    theme: str | None = None,
    target_units: list[str] | None = None,
    seed: int | None = None,
    level: int = 2,
) -> StoryPlan:
    rng = random.Random(seed)

    if theme:  # explicit theme: honour it, resolve key words if we know it
        chosen = _BY_TEXT.get(theme, Theme(theme))
    else:
        readable = [t for t in THEMES if _resolve(t, language, mastery)[0]]
        chosen = rng.choice(readable or THEMES)
    _, key_words, avoid_words = _resolve(chosen, language, mastery)

    words = decodable_words(language, mastery)
    if not target_units:
        pool = sorted(u for u in mastery if not u.startswith("w:"))
        target_units = rng.sample(pool, min(3, len(pool)))

    if len(words) > WORD_BANK_MAX:
        # keep key words and every word that exercises a target unit, fill the rest at random
        targets = [u.split(":", 1)[1] for u in target_units]
        focus = [w for w in words if w in key_words or any(t in w for t in targets)]
        focus_set = set(focus)
        rest = [w for w in words if w not in focus_set]
        rng.shuffle(focus)
        rng.shuffle(rest)
        words = sorted((focus + rest)[:WORD_BANK_MAX])

    return StoryPlan(
        language=language,
        learner_name=learner_name,
        theme=chosen.text,
        key_words=key_words,
        avoid_words=avoid_words,
        target_units=list(target_units),
        level=level,
        word_bank=words,
        mastery=sorted(mastery),
    )

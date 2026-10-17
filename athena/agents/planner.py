"""Planner: picks theme, focus units and the word bank the writer should draw from.

Deterministic (seeded RNG). No model call: the plan is cheap and must be explainable.
"""

import random

from athena.lexicon import decodable_words
from athena.models import Language, StoryPlan

THEMES = [
    "helping mother cook dal bhat in the kitchen",
    "a goat that wanders off in the village",
    "flying a kite on the rooftop during Dashain",
    "a rainy day walk to school",
    "feeding the hens in the morning",
    "a picnic by the river with family",
    "grandmother telling a story in the evening",
    "planting maize in the field",
    "a cat and a dog who become friends",
    "going to the market with father",
    "seeing the mountains on a clear morning",
    "a little bird building a nest",
]

WORD_BANK_MAX = 150


def plan(
    language: Language,
    mastery: frozenset[str],
    learner_name: str,
    theme: str | None = None,
    target_units: list[str] | None = None,
    seed: int | None = None,
) -> StoryPlan:
    rng = random.Random(seed)
    theme = theme or rng.choice(THEMES)
    words = decodable_words(language, mastery)

    if not target_units:
        pool = sorted(u for u in mastery if not u.startswith("w:"))
        target_units = rng.sample(pool, min(3, len(pool)))

    if len(words) > WORD_BANK_MAX:
        # keep every word that exercises a target unit, fill the rest at random
        targets = [u.split(":", 1)[1] for u in target_units]
        focus = [w for w in words if any(t in w for t in targets)]
        rest = [w for w in words if w not in set(focus)]
        rng.shuffle(focus)
        rng.shuffle(rest)
        words = sorted((focus + rest)[:WORD_BANK_MAX])

    return StoryPlan(
        language=language,
        learner_name=learner_name,
        theme=theme,
        target_units=list(target_units),
        word_bank=words,
        mastery=sorted(mastery),
    )

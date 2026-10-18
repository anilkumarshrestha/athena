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

# The child's favourite thing to do (onboarding): personal themes, used like favourite animal/food.
ACTIVITY_THEMES: dict[str, Theme] = {
    "kite": Theme("flying a kite with friends", ne=[["चङ्गा"]], en=[["kite", "kites"]]),
    "football": Theme("playing football with friends", ne=[["बल", "फुटबल"]], en=[["ball", "kick"]]),
    "dancing": Theme("dancing together at a festival", ne=[["नाच", "नाच्न"]], en=[["dance", "hop"]]),
    "drawing": Theme("drawing a picture", ne=[["चित्र"]], en=[["pen", "pens"]]),
    "singing": Theme("singing songs with family", ne=[["गीत"]], en=[["song", "sing"]]),
    "cycling": Theme("riding a bicycle on the path", ne=[["साइकल"]], en=[["bike"]]),
}

# For the "pick your story" tiles: (Nepali label, English label, picture noun). The child picks
# by picture; labels are for the adult. Picture nouns are concrete nouns (no people drawn).
THEME_TILES: dict[str, tuple[str, str, str]] = {
    "helping mother cook dal bhat in the kitchen": ("दाल भात पकाउने", "Cooking dal bhat", "भात"),
    "a goat that wanders off in the village": ("हराएको खसी", "The lost goat", "खसी"),
    "flying a kite on the rooftop during Dashain": ("चङ्गा उडाउने", "Flying a kite", "चङ्गा"),
    "a rainy day walk to school": ("पानी पर्दा स्कुल", "Rainy walk to school", "पानी"),
    "feeding the hens in the morning": ("कुखुरालाई दाना", "Feeding the hens", "कुखुरा"),
    "a picnic by the river with family": ("खोला किनारमा", "Picnic by the river", "खोला"),
    "grandmother telling a story in the evening": ("हजुरआमाको कथा", "Grandma's story", "घर"),
    "planting maize in the field": ("मकै रोप्ने", "Planting maize", "मकै"),
    "a cat and a dog who become friends": ("बिरालो र कुकुर", "Cat and dog", "बिरालो"),
    "going to the market with father": ("बुबासँग बजार", "Market with dad", "बजार"),
    "seeing the mountains on a clear morning": ("हिमाल हेर्ने", "Seeing the mountains", "हिमाल"),
    "a little bird building a nest": ("चराको गुँड", "A bird's nest", "चरा"),
    "flying a kite with friends": ("साथीसँग चङ्गा", "Kite with friends", "चङ्गा"),
    "playing football with friends": ("फुटबल खेल्ने", "Playing football", "बल"),
    "dancing together at a festival": ("चाडमा नाच", "Dancing at a festival", "घर"),
    "drawing a picture": ("चित्र बनाउने", "Drawing a picture", "किताब"),
    "singing songs with family": ("गीत गाउने", "Singing songs", "घर"),
    "riding a bicycle on the path": ("साइकल चलाउने", "Riding a bike", "बाटो"),
}


def tile_for(theme: Theme) -> tuple[str, str, str]:
    """(ne label, en label, picture noun) for a theme, personal ones included."""
    if theme.text in THEME_TILES:
        return THEME_TILES[theme.text]
    noun = theme.ne[0][0] if theme.ne and theme.ne[0] else "घर"
    if theme.text.startswith("eating "):  # favourite food: "eating dal bhat with family"
        en = theme.text.removeprefix("eating ").removesuffix(" with family")
        return (f"{noun} खाने", f"Eating {en}", noun)
    if "the child's " in theme.text:  # favourite animal: "a day with the child's goat"
        return (f"मेरो {noun}", f"My {theme.text.split('the child' + chr(39) + 's ')[-1]}", noun)
    return (theme.text, theme.text, noun)


def readable_themes(language: Language, mastery: frozenset[str], personal: list[Theme] | None = None) -> list[Theme]:
    return [t for t in [*(personal or []), *THEMES] if _resolve(t, language, mastery)[0]]


def base_theme(theme_text: str) -> str:
    """Theme without the ", in <setting>" suffix the planner adds."""
    return theme_text.split(", in ")[0]

WORD_BANK_MAX = 150
PERSONAL_SHARE = 0.6


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
    personal: list[Theme] | None = None,
    setting: str | None = None,
    child_gender: str = "unspecified",
    avoid: frozenset[str] = frozenset(),
) -> StoryPlan:
    """personal: themes from the child's favourites, preferred when readable.
    setting: where the child lives, e.g. "a hill village in Nepal" (story + picture)."""
    rng = random.Random(seed)

    if theme:  # explicit theme (e.g. the child picked it): honour it, personal ones included
        chosen = next((t for t in [*(personal or []), *THEMES] if t.text == theme), None) or _BY_TEXT.get(theme, Theme(theme))
    else:
        mine = [t for t in personal or [] if _resolve(t, language, mastery)[0]]
        allowed_themes = [t for t in THEMES if t.text not in avoid] or THEMES  # parent's "avoid" list
        readable = [t for t in allowed_themes if _resolve(t, language, mastery)[0]]
        # Favourites most of the time; general themes keep it from getting repetitive.
        chosen = rng.choice(mine) if mine and rng.random() < PERSONAL_SHARE else rng.choice(readable or allowed_themes)
    _, key_words, avoid_words = _resolve(chosen, language, mastery)
    theme_text = f"{chosen.text}, in {setting}" if setting else chosen.text

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
        theme=theme_text,
        key_words=key_words,
        avoid_words=avoid_words,
        target_units=list(target_units),
        level=level,
        child_gender=child_gender,
        word_bank=words,
        mastery=sorted(mastery),
    )

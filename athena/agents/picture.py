"""Picture cue for re-teaching ("see it"): one simple picture of a concrete noun.

Only concrete nouns get a picture (animals, food, objects, places, body, nature, from
the seed categories, plus a short English list); abstract words and verbs do not.
Case endings are stripped first (खसीले -> खसी). Generated once per word, cached on disk,
same flat style as story illustrations.
"""

import hashlib
from functools import lru_cache
from pathlib import Path

from google.genai import types

from athena.agents.illustrator import STYLE
from athena.config import genai_client, settings
from athena.lexicon import ne_seed
from athena.retry import with_retry
from athena.verifier.nepali import CASE_ENDINGS

CACHE = Path(__file__).resolve().parent.parent.parent / "media" / "pictures"
NE_CATEGORIES = {"animals", "food", "objects", "places", "body", "nature"}
EN_NOUNS = set(
    "cat dog hen pig sun cup ship fish duck bed hat map pen egg goat boat moon tree book car bus fox frog "
    "cow bird rain milk corn hill nest kite cake bell ball sock rock net van jam bag box lamp hand tent "
    "drum flag clock star farm coat seed queen train snail sheep feet light rope bone rose bike cube".split()
)


@lru_cache
def _ne_nouns() -> frozenset[str]:
    from athena.fallback import ANIMAL_ADJ, FOOD_ADJ, OBJECT_ADJ  # nouns stories use (खसी is not a seed word)
    from athena.profile import ANIMALS, FOODS

    seed = {e["word"] for e in ne_seed() if e["category"] in NE_CATEGORIES}
    profile = {w for _, ne, _ in [*ANIMALS.values(), *FOODS.values()] for w in ne}
    return frozenset(seed | set(ANIMAL_ADJ) | set(FOOD_ADJ) | set(OBJECT_ADJ) | profile)


def concrete_noun(language: str, word: str) -> str | None:
    """The base noun to picture, or None if this word should not get a picture."""
    if language == "en":
        w = word.lower()
        base = w[:-1] if w.endswith("s") and w[:-1] in EN_NOUNS else w
        return base if base in EN_NOUNS else None
    if word in _ne_nouns():
        return word
    for ending in CASE_ENDINGS:
        if word.endswith(ending) and word[: -len(ending)] in _ne_nouns():
            return word[: -len(ending)]
    return None


def picture(language: str, noun: str) -> tuple[bytes, str]:
    key = hashlib.sha256(f"{language}:{noun}".encode()).hexdigest()[:24]
    for ext, mime in (("jpeg", "image/jpeg"), ("png", "image/png")):
        p = CACHE / f"{key}.{ext}"
        if p.exists():
            return p.read_bytes(), mime
    lang_name = "Nepali" if language == "ne" else "English"
    r = with_retry(
        lambda: genai_client("image").models.generate_content(
            model=settings().image_model,
            contents=(
                f'One simple picture of the {lang_name} word "{noun}" for a young child learning to read: '
                f"a single object, centred, plain background, nothing else.\n\n{STYLE}"
            ),
            config=types.GenerateContentConfig(
                response_modalities=["IMAGE"], image_config=types.ImageConfig(aspect_ratio="1:1")
            ),
        ),
        "picture",
    )
    for part in r.candidates[0].content.parts:
        if part.inline_data and part.inline_data.data:
            mime = part.inline_data.mime_type or "image/png"
            CACHE.mkdir(parents=True, exist_ok=True)
            (CACHE / f"{key}.{'jpeg' if 'jpeg' in mime else 'png'}").write_bytes(part.inline_data.data)
            return part.inline_data.data, mime
    raise RuntimeError("no picture returned")

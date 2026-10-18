"""Picture cue for re-teaching ("see it"): one simple picture of a concrete noun.

Only concrete nouns get a picture (animals, food, objects, places, body, nature, from
the seed categories, plus a short English list); abstract words and verbs do not.
Case endings are stripped first (खसीले -> खसी). Generated once per word, cached on disk,
same flat style as story illustrations.
"""

import hashlib
import subprocess
import threading
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


_locks: dict[str, threading.Lock] = {}
_locks_guard = threading.Lock()
SIZE = 512  # shown at 160 px; 512 keeps it sharp on retina for ~50 KB instead of ~900 KB


def _shrink(data: bytes) -> bytes:
    """Model PNG (~900 KB, 1024 px) -> 512 px JPEG (~50 KB). Falls back to the original."""
    try:
        return subprocess.run(
            ["ffmpeg", "-loglevel", "error", "-i", "pipe:0", "-vf", f"scale={SIZE}:-1", "-q:v", "4", "-f", "mjpeg", "pipe:1"],
            input=data, capture_output=True, check=True, timeout=20,
        ).stdout
    except Exception:  # noqa: BLE001 - keep the big one rather than nothing
        return data


def _cached(key: str) -> tuple[bytes, str] | None:
    for ext, mime in (("jpeg", "image/jpeg"), ("png", "image/png")):
        p = CACHE / f"{key}.{ext}"
        if p.exists():
            return p.read_bytes(), mime
    return None


def picture(language: str, noun: str) -> tuple[bytes, str]:
    """One picture per (language, noun), shared by every child and story. Generated at most
    once even if several taps arrive while it is being drawn."""
    key = hashlib.sha256(f"{language}:{noun}".encode()).hexdigest()[:24]
    if hit := _cached(key):
        return hit
    with _locks_guard:
        lock = _locks.setdefault(key, threading.Lock())
    with lock:  # a second tap waits for the first generation instead of starting its own
        if hit := _cached(key):
            return hit
        lang_name = "Nepali" if language == "ne" else "English"
        r = with_retry(
            lambda: genai_client("image").models.generate_content(
                model=settings().image_model,
                contents=(
                    f"Draw the thing that the {lang_name} word {noun} names, for a young child: one single "
                    "object or animal, centred, plain background, nothing else. The picture must contain NO "
                    "writing at all: no words, no letters, no labels, no captions (the child is learning to "
                    f"read the word, so the picture must not show it).\n\n{STYLE}"
                ),
                config=types.GenerateContentConfig(
                    response_modalities=["IMAGE"], image_config=types.ImageConfig(aspect_ratio="1:1")
                ),
            ),
            "picture",
        )
        for part in r.candidates[0].content.parts:
            if part.inline_data and part.inline_data.data:
                data = _shrink(part.inline_data.data)
                mime = "image/jpeg" if data[:2] == b"\xff\xd8" else (part.inline_data.mime_type or "image/png")
                CACHE.mkdir(parents=True, exist_ok=True)
                (CACHE / f"{key}.{'jpeg' if mime == 'image/jpeg' else 'png'}").write_bytes(data)
                return data, mime
        raise RuntimeError("no picture returned")

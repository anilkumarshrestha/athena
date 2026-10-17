"""Data loading + verifier factory. Cached; data files are read once per process."""

import json
from functools import lru_cache
from pathlib import Path

from athena.verifier.base import Verifier
from athena.verifier.english import EnglishVerifier, LexEntry, load_lexicon
from athena.verifier.nepali import NepaliVerifier

DATA = Path(__file__).resolve().parent.parent / "data"


@lru_cache
def en_lexicon() -> dict[str, LexEntry]:
    return load_lexicon(DATA / "en_lexicon.json")


@lru_cache
def ne_seed() -> list[dict]:
    return json.loads((DATA / "ne_seed.json").read_text(encoding="utf-8"))


def verifier_for(language: str, mastery: frozenset[str], allowed_words: frozenset[str] = frozenset()) -> Verifier:
    if language == "ne":
        return NepaliVerifier(mastery, allowed_words)
    if language == "en":
        return EnglishVerifier(mastery, en_lexicon(), allowed_words)
    raise ValueError(f"unknown language {language!r}")


def decodable_words(language: str, mastery: frozenset[str]) -> list[str]:
    """Every known word the learner can read right now."""
    if language == "ne":
        return [e["word"] for e in ne_seed() if set(e["signatures"]) <= mastery]
    v = verifier_for("en", mastery)
    return [w for w in en_lexicon() if v.verify(w).ok]

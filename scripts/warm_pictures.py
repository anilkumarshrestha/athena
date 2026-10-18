"""Draw every letter-anchor picture once, into media/pictures (shipped in the image).

  .venv/bin/python scripts/warm_pictures.py

The help card shows "t → tent" with tent's picture; drawn on first use, a picture can be
blocked by the image quota and the card shows none. This draws them all ahead of time:
English anchors (athena/tts.py EN_ANCHORS) and the Nepali anchor words for every letter and
vowel sign. Only whitelisted concrete nouns (people are never drawn). Skips what exists.
"""

import hashlib
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from athena.agents.picture import CACHE, concrete_noun, picture  # noqa: E402
from athena.letters import example_word  # noqa: E402
from athena.progression import SEQUENCE  # noqa: E402
from athena.tts import EN_ANCHORS, anchor_word  # noqa: E402


def cached(lang: str, noun: str) -> bool:
    key = hashlib.sha256(f"{lang}:{noun}".encode()).hexdigest()[:24]
    return any((CACHE / f"{key}.{ext}").exists() for ext in ("jpeg", "png"))


def wanted() -> list[tuple[str, str]]:
    out: dict[tuple[str, str], None] = {}
    for word in EN_ANCHORS.values():
        out[("en", word)] = None
    for sig in SEQUENCE["ne"]:
        word = anchor_word("ne", sig[2:]) if sig[:2] == "c:" else example_word("ne", sig)
        if word:
            out[("ne", word)] = None
    return [(lang, concrete_noun(lang, w)) for lang, w in out if concrete_noun(lang, w)]


def main() -> None:
    todo = [(lang, n) for lang, n in dict.fromkeys(wanted()) if not cached(lang, n)]
    print(f"{len(todo)} pictures to draw", flush=True)
    for lang, noun in todo:
        for attempt in range(6):
            try:
                t0 = time.time()
                picture(lang, noun)
                print(f"{lang}:{noun} in {time.time() - t0:.0f}s", flush=True)
                break
            except Exception as e:  # noqa: BLE001 - quota: wait and retry
                print(f"  {lang}:{noun}: {type(e).__name__}, retry in {20 * (attempt + 1)}s", flush=True)
                time.sleep(20 * (attempt + 1))
        time.sleep(3)
    left = [f"{lang}:{n}" for lang, n in wanted() if not cached(lang, n)]
    print("still missing:", left or "none")


if __name__ == "__main__":
    main()

"""Synthesise the fixed spoken phrases once into media/sounds (shipped in the image).

  .venv/bin/python scripts/warm_sounds.py

The letter game's letters ("क, कमलको क", "a for apple") and the praise after reading are
the same for every child. Shipped, they play instantly even on a fresh Cloud Run instance
whose voice cache is empty. Re-run after changing tts.letter_phrase or the praise lines.
"""

import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import hashlib  # noqa: E402

from athena import tts  # noqa: E402
from athena.api import PHRASES, PRAISE  # noqa: E402
from athena.diagnostic import _EN_SET1, _EN_SET2, _NE_T1, _NE_T2  # noqa: E402


def main() -> None:
    phrases = [("ne", tts.letter_phrase("ne", x)) for x in _NE_T1 + _NE_T2]
    phrases += [("en", tts.letter_phrase("en", x)) for x in _EN_SET1 + _EN_SET2]
    phrases += [(lang, text) for lang, tiers in PRAISE.items() for text in tiers.values()]
    phrases += [(lang, text) for lang, keys in PHRASES.items() for text in keys.values()]
    tts.SHIPPED.mkdir(parents=True, exist_ok=True)
    for lang, text in dict.fromkeys(phrases):
        key = hashlib.sha256(f"v2:{lang}:{text}".encode()).hexdigest()[:24]
        target = tts.SHIPPED / f"{key}.wav"
        if target.exists():
            continue
        tts.speak_word(lang, text)  # synthesises into the cache (or finds it there)
        shutil.copy(tts.CACHE / f"{key}.wav", target)
        print(f"{lang}: {text}", flush=True)
    files = list(tts.SHIPPED.glob("*.wav"))
    print(f"{len(files)} shipped sounds, {sum(f.stat().st_size for f in files) // 1024} KB")


if __name__ == "__main__":
    main()

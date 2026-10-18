"""Grown-up gloss for a Nepali story: romanisation (in code) + an English translation (model).

For visitors who do not read Devanagari (judges, many parents abroad): each sentence shown as

    सीताको सानो खैरो खसी छ।
    sītāko sāno khairo khasī cha — "Sita has a small brown goat."

Romanisation is deterministic: consonants carry an inherent "a", vowel signs replace it,
virama removes it, and as in spoken Nepali a word-final inherent "a" is not said (घर -> ghar).
The translation is one Flash-Lite call per story, cached on disk by the sentences. It is shown
to grown-ups only, never as reading material for the child.
"""

import hashlib
import json
from pathlib import Path

from google.genai import types
from pydantic import BaseModel

from athena.config import genai_client
from athena.retry import with_retry

CACHE = Path(__file__).resolve().parent.parent / "media" / "gloss"
MODEL = "gemini-3.1-flash-lite"

VOWELS = {"अ": "a", "आ": "ā", "इ": "i", "ई": "ī", "उ": "u", "ऊ": "ū", "ऋ": "ri", "ए": "e", "ऐ": "ai", "ओ": "o", "औ": "au"}
SIGNS = {"ा": "ā", "ि": "i", "ी": "ī", "ु": "u", "ू": "ū", "ृ": "ri", "े": "e", "ै": "ai", "ो": "o", "ौ": "au"}
CONSONANTS = {
    "क": "k", "ख": "kh", "ग": "g", "घ": "gh", "ङ": "ṅ", "च": "c", "छ": "ch", "ज": "j", "झ": "jh", "ञ": "ñ",
    "ट": "ṭ", "ठ": "ṭh", "ड": "ḍ", "ढ": "ḍh", "ण": "ṇ", "त": "t", "थ": "th", "द": "d", "ध": "dh", "न": "n",
    "प": "p", "फ": "ph", "ब": "b", "भ": "bh", "म": "m", "य": "y", "र": "r", "ल": "l", "व": "w",
    "श": "ś", "ष": "ṣ", "स": "s", "ह": "h",
}
MARKS = {"ं": "ṃ", "ँ": "̃", "ः": "ḥ"}
VIRAMA = "्"
DIGITS = str.maketrans("०१२३४५६७८९", "0123456789")
PUNCT = {"।": ".", "॥": "."}


def _word(w: str) -> str:
    out: list[str] = []
    for i, ch in enumerate(w):
        if ch in CONSONANTS:
            out.append(CONSONANTS[ch] + "a")  # inherent a, removed by a sign or virama
        elif ch in SIGNS and out and out[-1].endswith("a"):
            out[-1] = out[-1][:-1] + SIGNS[ch]
        elif ch == VIRAMA and out and out[-1].endswith("a"):
            out[-1] = out[-1][:-1]
        elif ch in VOWELS:
            out.append(VOWELS[ch])
        elif ch in MARKS:
            out.append(MARKS[ch])
        elif ch in PUNCT:
            out.append(PUNCT[ch])
        else:
            out.append(ch.translate(DIGITS))
    s = "".join(out)
    # spoken Nepali drops a word-final inherent a after a consonant (घर ghar, not ghara)
    core = s.rstrip(".?!,")
    tail = s[len(core):]
    letters = sum(ch in CONSONANTS or ch in VOWELS for ch in w)  # one syllable keeps its a: छ cha
    if letters > 1 and core.endswith("a") and w.rstrip("।?!,")[-1:] in CONSONANTS:
        core = core[:-1]
    return core + tail


def romanise(text: str) -> str:
    return " ".join(_word(w) for w in text.split())


class _Translation(BaseModel):
    english: list[str]


def translate(sentences: list[str]) -> list[str]:
    """Plain English, one line per sentence, cached by the exact sentences."""
    key = hashlib.sha256("\n".join(sentences).encode()).hexdigest()[:24]
    path = CACHE / f"{key}.json"
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    r = with_retry(
        lambda: genai_client().models.generate_content(
            model=MODEL,
            contents=(
                "Translate each sentence of this Nepali children's story into simple, natural English. "
                "Keep names as they are. Exactly one English sentence per Nepali sentence, same order.\n\n"
                + "\n".join(f"{i + 1}. {s}" for i, s in enumerate(sentences))
            ),
            config=types.GenerateContentConfig(
                response_mime_type="application/json", response_schema=_Translation, temperature=0
            ),
        ),
        "gloss",
    )
    t = r.parsed if isinstance(r.parsed, _Translation) else _Translation.model_validate_json(r.text or "")
    english = (t.english + [""] * len(sentences))[: len(sentences)]
    CACHE.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(english, ensure_ascii=False), encoding="utf-8")
    return english


def gloss(title: str, sentences: list[str]) -> dict:
    """{"title": {...}, "sentences": [{"text", "roman", "english"}]} for a Nepali story."""
    lines = [title, *sentences]
    english = translate(lines)
    rows = [{"text": t, "roman": romanise(t), "english": e} for t, e in zip(lines, english)]
    return {"title": rows[0], "sentences": rows[1:]}

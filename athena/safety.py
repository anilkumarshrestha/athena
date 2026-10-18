"""Content safety for stories shown to children (PLAN §11: blocklist + model check).

Two stages, cheapest first:
  1. blocklist (code): violence, death, fear, weapons, alcohol/tobacco, insults,
     matched on word stems so case endings are caught (भूतले, killed).
  2. model screen: a small, fast model (Gemini Flash-Lite) classifies the whole
     story for a 5-8 year old: catches what words alone miss ("left alone at night").

Fails closed: if the model screen errors, the story is treated as unsafe and the
caller serves a curated template instead. Vertex AI safety filters stay on as well.
"""

from dataclasses import dataclass

from google.genai import types
from pydantic import BaseModel

from athena.config import genai_client, settings
from athena.retry import with_retry
from athena.verifier.english import tokenize as en_tokenize
from athena.verifier.nepali import tokenize as ne_tokenize

# Stems: a token matches if it starts with one (Nepali inflects by suffix).
BLOCK_NE = (
    "मार मर्यो मरे मर्छ मृत्यु लास रगत घाउ बन्दुक चक्कु छुरा तरवार बम युद्ध लडाइँ झगडा कुट हान "
    "भूत बोक्सी डर डरा डराउ रुवा चोर अपहरण रक्सी चुरोट जाँड गाली मूर्ख"
).split()
BLOCK_EN = (
    "kill dead die died dying death blood gun knife sword bomb war fight hurt "  # hit/kick: a ball game is fine
    "ghost witch monster scary scared afraid fear thief steal beer wine smoke stupid hate"
).split()
# Short English stems would over-match (hit -> hitch): English matches whole words or -s/-ed/-ing.
_EN_SUFFIXES = ("", "s", "ed", "d", "ing", "er", "y")


@dataclass(frozen=True)
class SafetyResult:
    safe: bool
    stage: str  # "ok" | "blocklist" | "model" | "error"
    reason: str = ""


def blocklisted(language: str, words: list[str]) -> list[str]:
    hits = []
    for w in words:
        if language == "ne":
            if any(w.startswith(stem) for stem in BLOCK_NE):
                hits.append(w)
        else:
            lw = w.lower()
            if any(lw == stem + suf for stem in BLOCK_EN for suf in _EN_SUFFIXES):
                hits.append(w)
    return hits


class _Verdict(BaseModel):
    safe: bool
    reason: str


def _model_screen(language: str, text: str) -> tuple[bool, str]:
    lang = "Nepali" if language == "ne" else "English"
    r = with_retry(
        lambda: genai_client().models.generate_content(
            model=settings().safety_model,
            contents=(
                f"You check stories for children aged 5-8 in Nepal before they are shown. Story ({lang}):\n\n"
                f"{text}\n\nUnsafe if it has violence, injury, death, fear or horror, danger to the child, "
                "adult themes, insults, alcohol or tobacco, or anything a parent would not want a young "
                "child to read. Everyday sadness resolved kindly is fine. Answer with safe and a short reason."
            ),
            config=types.GenerateContentConfig(
                response_mime_type="application/json", response_schema=_Verdict, temperature=0
            ),
        ),
        "safety",
    )
    v = r.parsed if isinstance(r.parsed, _Verdict) else _Verdict.model_validate_json(r.text or "")
    return v.safe, v.reason


def check(language: str, title: str, sentences: list[str], model: bool = True) -> SafetyResult:
    tokenize = ne_tokenize if language == "ne" else en_tokenize
    words = tokenize("\n".join([title, *sentences]))
    hits = blocklisted(language, words)
    if hits:
        return SafetyResult(False, "blocklist", "blocked words: " + " ".join(hits))
    if not model:
        return SafetyResult(True, "ok")
    try:
        safe, reason = _model_screen(language, "\n".join([title, *sentences]))
    except Exception as e:  # noqa: BLE001 - fail closed
        return SafetyResult(False, "error", f"safety screen unavailable: {type(e).__name__}")
    return SafetyResult(safe, "ok" if safe else "model", reason)

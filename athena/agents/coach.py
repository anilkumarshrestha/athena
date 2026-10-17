"""Coach: home activities for parents, around the units the child is practising.

The model suggests activities; code decides which words the child is shown: every
child-facing word is run through the verifier against the child's current units, and
dropped if unreadable. Practice words also come straight from code (readable words
that contain a practising unit), so the list is useful even if the model fails.
Cached per learner, language and day.
"""

import time
from datetime import date

from google.genai import types
from pydantic import BaseModel, Field

from athena.config import genai_client, settings
from athena.lexicon import decodable_words, verifier_for
from athena.retry import with_retry


class Activity(BaseModel):
    title_ne: str
    title_en: str
    how_ne: str = Field(description="1-2 short sentences for the parent, polite तपाईं forms")
    how_en: str
    child_words: list[str] = Field(description="up to 4 words for the child to read")


class Activities(BaseModel):
    activities: list[Activity]


_cache: dict[tuple[str, str, str], tuple[list[dict], list[str]]] = {}


def practice_words(language: str, allowed: frozenset[str], practicing: list[str], n: int = 8) -> list[str]:
    """Readable words that exercise a practising unit (pure code)."""
    glyphs = [u.split(":", 1)[1] for u in practicing]
    words = [w for w in decodable_words(language, allowed) if any(g in w for g in glyphs)]
    return sorted(words, key=len)[:n]


def activities(learner_id: str, language: str, name: str, allowed: frozenset[str], practicing: list[str],
               interests: str) -> tuple[list[dict], list[str]]:
    key = (learner_id, language, date.today().isoformat())
    if key in _cache:
        return _cache[key]
    words = practice_words(language, allowed, practicing)
    focus = ", ".join(u.split(":", 1)[1] for u in practicing) or "the letters they know"
    prompt = f"""You help parents in Nepal support a 5-8 year old learning to read {"Nepali" if language == "ne" else "English"}.
Child: {name}. Likes: {interests}. Practising now: {focus}.
Words the child can already read that use these: {" ".join(words) or "(few yet)"}

Suggest 3 playful home activities, about 5 minutes each, using everyday household things.
No screens, nothing to buy, no worksheets. Warm and simple. Write for the parent, both Nepali
(polite तपाईं forms, natural everyday Nepali) and English. child_words: up to 4 words from the
list above for the child to read during the activity."""
    out: list[dict] = []
    try:
        r = with_retry(
            lambda: genai_client().models.generate_content(
                model=settings().writer_model,
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=Activities,
                    thinking_config=types.ThinkingConfig(thinking_level="low"),
                    temperature=0.7,
                    max_output_tokens=4096,
                ),
            ),
            "coach",
        )
        acts = r.parsed if isinstance(r.parsed, Activities) else Activities.model_validate_json(r.text or "")
        v = verifier_for(language, allowed)
        for a in acts.activities[:3]:
            d = a.model_dump()
            d["child_words"] = [w for w in a.child_words if v.verify(w).ok][:4]  # code decides
            out.append(d)
    except Exception:  # noqa: BLE001 - the practice words below still help
        out = []
    _cache[key] = (out, words)
    return out, words


def _clear_old(now: float | None = None) -> None:
    today = date.fromtimestamp(now or time.time()).isoformat()
    for k in [k for k in _cache if k[2] != today]:
        _cache.pop(k, None)

"""One call to each model we depend on. Prints OK/FAIL + latency. Run: python scripts/smoke.py"""

import time
import traceback
from pathlib import Path

from google.genai import types

from athena.config import genai_client, settings
from athena.verifier.nepali import NepaliVerifier, decompose

OUT = Path(__file__).resolve().parent / "smoke_out"


def run(name: str, fn) -> None:
    t0 = time.perf_counter()
    try:
        detail = fn()
        print(f"OK    {name:<14} {time.perf_counter() - t0:5.1f}s  {detail}")
    except Exception as e:
        print(f"FAIL  {name:<14} {time.perf_counter() - t0:5.1f}s  {type(e).__name__}: {e}")
        traceback.print_exc(limit=1)


def gemini_text() -> str:
    s = settings()
    r = genai_client().models.generate_content(
        model=s.writer_model,
        contents="एउटा ५ वर्षको बच्चाको लागि गाउँ, आमा र बिरालोबारे तीन वाक्यको सानो कथा नेपालीमा लेख। कथा मात्र लेख।",
    )
    text = (r.text or "").strip()
    # sanity: does the verifier parse what the model wrote?
    words = text.split()
    mastery = frozenset().union(*(u.signatures() for w in words for u in _safe(w)))
    res = NepaliVerifier(mastery).verify(text)
    malformed = [v.word for v in res.violations if v.unit is None]
    return f"{r.model_version}  words={res.words_checked} malformed={malformed}\n      {text[:160]}"


def _safe(word: str):
    try:
        return decompose(word)
    except ValueError:
        return []


def gemma() -> str:
    s = settings()
    r = genai_client().models.generate_content(
        model=s.cheap_model,
        contents="Classify this children's story text as SAFE or UNSAFE. Reply with one word.\n\nआमा र बिरालो घरमा छन्।",
    )
    return f"{r.model_version}  -> {(r.text or '').strip()!r}"


def gemini_image() -> str:
    s = settings()
    r = genai_client().models.generate_content(
        model=s.image_model,
        contents=(
            "Simple flat vector illustration for a children's picture book: a small cat sitting in the "
            "courtyard of a Nepali village house with hills behind. Warm soft colors, no text, "
            "no human faces in detail."
        ),
        config=types.GenerateContentConfig(response_modalities=["IMAGE", "TEXT"]),
    )
    for part in r.candidates[0].content.parts:
        if part.inline_data and part.inline_data.data:
            OUT.mkdir(exist_ok=True)
            ext = (part.inline_data.mime_type or "image/png").split("/")[-1]
            path = OUT / f"cat.{ext}"
            path.write_bytes(part.inline_data.data)
            return f"{r.model_version}  {len(part.inline_data.data) // 1024} KB -> {path.relative_to(OUT.parent.parent)}"
    raise RuntimeError(f"no image in response: {r.text!r}")


def stt() -> str:
    try:
        import google.auth

        google.auth.default()
    except Exception:
        return "SKIPPED (no gcloud ADC yet; needs `gcloud auth application-default login`)"
    return "SKIPPED (ADC found; Cloud STT test lands at H7)"


if __name__ == "__main__":
    s = settings()
    print(f"backend: {'vertex' if s.google_genai_use_vertexai else 'ai-studio'}\n")
    run("gemini-text", gemini_text)
    run("gemma", gemma)
    run("gemini-image", gemini_image)
    run("stt-ne", stt)

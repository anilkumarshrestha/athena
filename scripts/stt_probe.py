"""Nepali STT bake-off on a known reference sentence.

Synthesizes the reference with Gemini TTS, then transcribes with each candidate.
Synthetic adult-ish voice: validates language support + pipeline, NOT child accuracy.
"""

import difflib
import io
import time
import wave

from google.api_core.client_options import ClientOptions
from google.cloud.speech_v2 import SpeechClient
from google.cloud.speech_v2.types import cloud_speech as cs
from google.genai import types

from athena.config import genai_client, settings
from athena.verifier.nepali import tokenize

REFERENCE = "आमा र बिरालो घरमा छन्। बिरालो दूध पिउँछ। आमा हाँस्नुहुन्छ।"
TTS_MODEL = "gemini-3.8-flash-tts"
TRANSCRIBE_MODEL = "gemini-3.5-transcribe"


def synth() -> bytes:
    r = genai_client().models.generate_content(
        model=TTS_MODEL,
        contents=f"Read this Nepali text slowly and clearly, like a child reading aloud: {REFERENCE}",
        config=types.GenerateContentConfig(response_modalities=["AUDIO"]),
    )
    part = r.candidates[0].content.parts[0].inline_data
    rate = int(part.mime_type.split("rate=")[-1]) if "rate=" in part.mime_type else 24000
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rate)
        w.writeframes(part.data)
    return buf.getvalue()


def word_match(hyp: str) -> str:
    ref, h = tokenize(REFERENCE), tokenize(hyp)
    sm = difflib.SequenceMatcher(a=ref, b=h, autojunk=False)
    hits = sum(b.size for b in sm.get_matching_blocks())
    return f"{hits}/{len(ref)} words exact"


def cloud_stt(audio: bytes, location: str, model: str, hints: bool) -> str:
    endpoint = "speech.googleapis.com" if location == "global" else f"{location}-speech.googleapis.com"
    client = SpeechClient(client_options=ClientOptions(api_endpoint=endpoint))
    config = cs.RecognitionConfig(
        auto_decoding_config=cs.AutoDetectDecodingConfig(), language_codes=["ne-NP"], model=model
    )
    if hints:
        phrases = [cs.PhraseSet.Phrase(value=w, boost=10) for w in sorted(set(tokenize(REFERENCE)))]
        config.adaptation = cs.SpeechAdaptation(
            phrase_sets=[cs.SpeechAdaptation.AdaptationPhraseSet(inline_phrase_set=cs.PhraseSet(phrases=phrases))]
        )
    project = settings().google_cloud_project
    r = client.recognize(
        request=cs.RecognizeRequest(
            recognizer=f"projects/{project}/locations/{location}/recognizers/_", config=config, content=audio
        )
    )
    return " ".join(res.alternatives[0].transcript for res in r.results if res.alternatives)


def gemini_transcribe(audio: bytes, model: str) -> str:
    r = genai_client().models.generate_content(
        model=model,
        contents=[
            types.Part.from_bytes(data=audio, mime_type="audio/wav"),
            "Transcribe this Nepali speech exactly as spoken, in Devanagari. Output only the transcript.",
        ],
    )
    return (r.text or "").strip()


def run(name: str, fn) -> None:
    t0 = time.perf_counter()
    try:
        hyp = fn()
        print(f"OK    {name:<30} {time.perf_counter() - t0:5.1f}s  {word_match(hyp)}\n      {hyp}")
    except Exception as e:
        print(f"FAIL  {name:<30} {time.perf_counter() - t0:5.1f}s  {type(e).__name__}: {str(e)[:200]}")


if __name__ == "__main__":
    print(f"reference: {REFERENCE}\n")
    audio = synth()
    print(f"synth: {len(audio) // 1024} KB wav\n")
    for loc, model in [("us", "chirp_3"), ("us-central1", "chirp_2"), ("global", "short"), ("global", "long")]:
        for hints in (False, True):
            run(f"cloud {model}@{loc}{' +hints' if hints else ''}", lambda: cloud_stt(audio, loc, model, hints))
    run(f"gemini {TRANSCRIBE_MODEL}", lambda: gemini_transcribe(audio, TRANSCRIBE_MODEL))
    run(f"gemini {settings().writer_model}", lambda: gemini_transcribe(audio, settings().writer_model))

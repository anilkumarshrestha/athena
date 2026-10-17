"""Speech-to-text for read-aloud audio. Audio is processed in memory and never stored.

Primary: Cloud Speech-to-Text v2, chirp_3 @ us, with the story's words as an inline
phrase set (probe 17 Oct: 10/10 words with hints vs 7/10 without).
Fallback: Gemini audio transcription, told not to correct the child.

Caveat (eval C): hints bias toward the reference and can hide real errors.
"""

import logging
import time
from dataclasses import dataclass
from functools import lru_cache

from google.api_core.client_options import ClientOptions
from google.genai import types

from athena.config import genai_client, settings
from athena.retry import with_retry

log = logging.getLogger("athena")

LANG_CODE = {"ne": "ne-NP", "en": "en-US"}
STT_LOCATION = "us"
STT_MODEL = "chirp_3"
HINT_BOOST = 10.0


@dataclass(frozen=True)
class Transcript:
    text: str
    engine: str
    latency_ms: int


@lru_cache
def _speech_client():
    from google.cloud.speech_v2 import SpeechClient

    return SpeechClient(client_options=ClientOptions(api_endpoint=f"{STT_LOCATION}-speech.googleapis.com"))


def _cloud_stt(lang: str, audio: bytes, phrases: list[str]) -> str:
    from google.cloud.speech_v2.types import cloud_speech as cs

    config = cs.RecognitionConfig(
        auto_decoding_config=cs.AutoDetectDecodingConfig(),
        language_codes=[LANG_CODE[lang]],
        model=STT_MODEL,
    )
    if phrases:
        config.adaptation = cs.SpeechAdaptation(
            phrase_sets=[
                cs.SpeechAdaptation.AdaptationPhraseSet(
                    inline_phrase_set=cs.PhraseSet(
                        phrases=[cs.PhraseSet.Phrase(value=p, boost=HINT_BOOST) for p in phrases]
                    )
                )
            ]
        )
    project = settings().google_cloud_project
    r = _speech_client().recognize(
        request=cs.RecognizeRequest(
            recognizer=f"projects/{project}/locations/{STT_LOCATION}/recognizers/_", config=config, content=audio
        ),
        timeout=30,
    )
    return " ".join(res.alternatives[0].transcript for res in r.results if res.alternatives)


def _gemini(lang: str, audio: bytes, mime: str) -> str:
    language = "Nepali (write in Devanagari)" if lang == "ne" else "English"
    r = with_retry(
        lambda: genai_client().models.generate_content(
            model=settings().writer_model,
            contents=[
                types.Part.from_bytes(data=audio, mime_type=mime),
                f"A young child is reading aloud in {language}. Transcribe EXACTLY what the child says, "
                "including mispronounced words, repeated words and false starts. Do NOT correct mistakes "
                "and do NOT guess the intended text. Output only the transcript.",
            ],
            config=types.GenerateContentConfig(temperature=0),
        ),
        "stt-gemini",
    )
    return (r.text or "").strip()


def transcribe(lang: str, audio: bytes, mime: str, phrases: list[str], hints: bool = True) -> Transcript:
    t0 = time.perf_counter()
    try:
        text = _cloud_stt(lang, audio, phrases if hints else [])
        engine = f"{STT_MODEL}{'+hints' if hints else ''}"
    except Exception:
        log.exception("cloud STT failed, falling back to Gemini")
        text = _gemini(lang, audio, mime.split(";")[0])
        engine = f"gemini:{settings().writer_model}"
    return Transcript(text=text, engine=engine, latency_ms=int((time.perf_counter() - t0) * 1000))

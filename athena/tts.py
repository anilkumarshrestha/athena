"""Text-to-speech for single story words (re-teach: "hear it").

Gemini TTS: Cloud Text-to-Speech has no Nepali voice. The text sent is the bare word;
an instruction in the prompt gets read aloud (seen in the STT probe). Output is raw
24 kHz 16-bit mono PCM, wrapped as WAV. Cached on disk by language + word, so each
word is synthesised once.
"""

import hashlib
import io
import wave
from pathlib import Path

from google.genai import types

from athena.config import genai_client
from athena.retry import with_retry

TTS_MODEL = "gemini-3.8-flash-tts"
CACHE = Path(__file__).resolve().parent.parent / "media" / "tts"


def _wav(pcm: bytes, rate: int = 24000) -> bytes:
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rate)
        w.writeframes(pcm)
    return buf.getvalue()


def speak_word(language: str, word: str) -> bytes:
    key = hashlib.sha256(f"{language}:{word}".encode()).hexdigest()[:24]
    path = CACHE / f"{key}.wav"
    if path.exists():
        return path.read_bytes()
    r = with_retry(
        lambda: genai_client().models.generate_content(
            model=TTS_MODEL,
            contents=word,
            config=types.GenerateContentConfig(response_modalities=["AUDIO"]),
        ),
        "tts",
    )
    part = r.candidates[0].content.parts[0].inline_data
    data = part.data
    if not data.startswith(b"RIFF"):
        mime = part.mime_type or ""
        rate = int(mime.split("rate=")[-1]) if "rate=" in mime else 24000
        data = _wav(data, rate)
    CACHE.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    return data

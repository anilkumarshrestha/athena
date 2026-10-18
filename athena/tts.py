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
# Telling the model the language fixes guessed pronunciations (ह read as "he").
LANG_CODE = {"ne": "ne-NP", "en": "en-US"}
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
    key = hashlib.sha256(f"v2:{language}:{word}".encode()).hexdigest()[:24]  # v2: with language code
    path = CACHE / f"{key}.wav"
    if path.exists():
        return path.read_bytes()
    r = with_retry(
        lambda: genai_client().models.generate_content(
            model=TTS_MODEL,
            contents=word,
            config=types.GenerateContentConfig(
                response_modalities=["AUDIO"],
                speech_config=types.SpeechConfig(language_code=LANG_CODE.get(language, "en-US")),
            ),
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


def letter_phrase(language: str, letter: str) -> str:
    """How a teacher says a letter so it cannot be misheard.
    Nepali: "ह, हातको ह" (the letter anchored in a familiar word, as in class: "क, कमलको क").
    English: "a for apple", as English letters are taught in Nepali classrooms: the letter's
    name, then a word that starts with its sound. (A true phonics sound needs recorded audio:
    a TTS reads a lone "a" as its name, and the TTS model accepts no system instruction.)
    Two-letter sounds that never start a word: "ck, as in duck"."""
    from athena.letters import example_word

    sig = ("c:" if language == "ne" else "g:") + letter
    word = example_word(language, sig)
    if language == "ne":
        return f"{letter}, {word}को {letter}" if word and word != letter else letter
    # Phonics anchors: the word must START with the letter's short sound (not "cat" for a).
    anchor = EN_ANCHORS.get(letter) or word
    if not anchor or anchor == letter:
        return letter
    return f"{letter} for {anchor}" if anchor.startswith(letter) else f"{letter}, as in {anchor}"


EN_ANCHORS = {
    "s": "sun", "a": "apple", "t": "tent", "p": "pig", "i": "insect", "n": "net",
    "m": "map", "d": "dog", "g": "goat", "o": "octopus", "c": "cat", "k": "kite",
    "e": "egg", "u": "umbrella", "r": "rain", "h": "hat", "b": "bed", "f": "fish", "l": "leg",
}

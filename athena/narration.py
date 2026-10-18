""""Read to me": a story read aloud sentence by sentence, with a start/end time per word so
the page can light each word as it is spoken (karaoke).

Audio: Gemini TTS per sentence (natural prosody; cached like word audio).
Timings: speech-to-text with word time offsets run over our own TTS audio (once, cached),
matched to the story's words. If that fails, timings are estimated from word length.
"""

import hashlib
import io
import json
import logging
import wave
from pathlib import Path

from athena.assess.align import fold, tokens
from athena.tts import CACHE as TTS_CACHE
from athena.tts import speak_word

log = logging.getLogger("athena")
TIMING_CACHE = TTS_CACHE.parent / "timings"
LANG_CODE = {"ne": "ne-NP", "en": "en-US"}


def _pcm(wav_bytes: bytes) -> tuple[bytes, int, float]:
    with wave.open(io.BytesIO(wav_bytes)) as w:
        rate = w.getframerate()
        frames = w.readframes(w.getnframes())
    return frames, rate, len(frames) / 2 / rate


def _estimate(words: list[str], duration: float) -> list[tuple[float, float]]:
    """Fallback: share the sentence time by word length (small lead-in and tail)."""
    lead, tail = 0.15, 0.25
    weights = [max(1, len(w)) + 1 for w in words]  # +1: the gap after each word
    span = max(0.1, duration - lead - tail)
    out, t = [], lead
    for w in weights:
        d = span * w / sum(weights)
        out.append((round(t, 2), round(t + d * 0.85, 2)))
        t += d
    return out


def _stt_offsets(language: str, pcm: bytes, rate: int, phrases: list[str]) -> list[tuple[str, float, float]]:
    from google.api_core.client_options import ClientOptions
    from google.cloud import speech_v1 as sp

    from athena.config import settings

    client = sp.SpeechClient(client_options=ClientOptions(quota_project_id=settings().google_cloud_project or None))
    r = client.recognize(
        config=sp.RecognitionConfig(
            encoding=sp.RecognitionConfig.AudioEncoding.LINEAR16,
            sample_rate_hertz=rate,
            language_code=LANG_CODE[language],
            enable_word_time_offsets=True,
            speech_contexts=[sp.SpeechContext(phrases=phrases, boost=15)],
        ),
        audio=sp.RecognitionAudio(content=pcm),
        timeout=20,
    )
    return [
        (w.word, w.start_time.total_seconds(), w.end_time.total_seconds())
        for res in r.results
        for w in res.alternatives[0].words
    ]


def _timings(language: str, sentence: str, wav: bytes) -> list[tuple[float, float]]:
    words = tokens(language, sentence)
    pcm, rate, duration = _pcm(wav)
    try:
        heard = _stt_offsets(language, pcm, rate, sorted(set(words)))
    except Exception:  # noqa: BLE001
        log.warning("narration timing STT failed; estimating")
        return _estimate(words, duration)
    # Greedy in-order match of heard words to the sentence's words (pronunciation fold).
    out: list[tuple[float, float] | None] = [None] * len(words)
    j = 0
    for w, start, end in heard:
        hw = fold(language, tokens(language, w)[0]) if tokens(language, w) else ""
        for k in range(j, min(j + 3, len(words))):
            if fold(language, words[k]) == hw:
                out[k] = (round(start, 2), round(end, 2))
                j = k + 1
                break
    if sum(x is not None for x in out) < max(1, len(words) // 2):
        return _estimate(words, duration)
    # Fill gaps (unmatched words) between known neighbours.
    est = _estimate(words, duration)
    return [x if x is not None else est[i] for i, x in enumerate(out)]


def narrate(language: str, sentences: list[str]) -> list[dict]:
    """[{text, audio_key, words: [{index, start, end}]}], word indices over the whole story."""
    out, base = [], 0
    for sentence in sentences:
        wav = speak_word(language, sentence)  # cached per text, language-coded
        key = hashlib.sha256(f"v2:{language}:{sentence}".encode()).hexdigest()[:24]
        tpath = TIMING_CACHE / f"{key}.json"
        if tpath.exists():
            timings = [tuple(x) for x in json.loads(tpath.read_text())]
        else:
            timings = _timings(language, sentence, wav)
            TIMING_CACHE.mkdir(parents=True, exist_ok=True)
            tpath.write_text(json.dumps(timings))
        n = len(tokens(language, sentence))
        out.append({
            "text": sentence,
            "audio_key": key,
            "words": [{"index": base + i, "start": s, "end": e} for i, (s, e) in enumerate(timings[:n])],
        })
        base += n
    return out


def audio_path(key: str) -> Path | None:
    p = TTS_CACHE / f"{key}.wav"
    return p if p.exists() else None

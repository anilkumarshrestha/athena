"""Streaming speech-to-text for live follow-along (Cloud Speech-to-Text v1, default model).

Latency probe, 18 Oct (time until each word of a 5 s Nepali sentence was reached):
  v2 chirp_3   whole sentences only
  v2 long      first words after ~3.0 s, then bursts
  v1 default   + story words as phrase hints: first word 0.5-0.7 s, ~0.4 s per word, none missed
Hints are fine here: the live view only guides, it never scores (hints can hide errors).
Final scoring still uses Chirp 3 on the full recording. Audio is relayed, never stored.

Input: 16 kHz mono LINEAR16 chunks. The gRPC call runs on its own thread; transcripts
are pushed to `on_text` (called from that thread).
"""

import logging
import queue
import threading
from collections.abc import Callable

from google.api_core.client_options import ClientOptions

from athena.config import settings

log = logging.getLogger("athena")

LANG_CODE = {"ne": "ne-NP", "en": "en-US"}
HINT_BOOST = 15.0
SAMPLE_RATE = 16000
MAX_SECONDS = 180  # a story read takes under a minute; stream limit is 5 min
MAX_BYTES = SAMPLE_RATE * 2 * MAX_SECONDS

_client = None
_client_lock = threading.Lock()


def _speech():
    global _client
    with _client_lock:
        if _client is None:
            from google.cloud import speech_v1

            _client = speech_v1.SpeechClient(
                client_options=ClientOptions(quota_project_id=settings().google_cloud_project or None)
            )
    return _client


class StreamSession:
    def __init__(
        self,
        language: str,
        on_text: Callable[[str], None],
        on_done: Callable[[str | None], None],
        phrases: list[str] | None = None,
    ) -> None:
        self.language = language
        self.phrases = phrases or []
        self.on_text = on_text
        self.on_done = on_done  # called once with an error message, or None
        self.audio: queue.Queue[bytes | None] = queue.Queue()
        self.sent = 0
        self.thread = threading.Thread(target=self._run, daemon=True, name="stt-stream")

    def start(self) -> None:
        self.thread.start()

    def feed(self, chunk: bytes) -> bool:
        """False once the per-session audio cap is reached."""
        if self.sent + len(chunk) > MAX_BYTES:
            return False
        self.sent += len(chunk)
        self.audio.put(chunk)
        return True

    def close(self) -> None:
        self.audio.put(None)

    def _config(self):
        from google.cloud import speech_v1 as sp

        return sp.StreamingRecognitionConfig(
            config=sp.RecognitionConfig(
                encoding=sp.RecognitionConfig.AudioEncoding.LINEAR16,
                sample_rate_hertz=SAMPLE_RATE,
                language_code=LANG_CODE[self.language],
                speech_contexts=[sp.SpeechContext(phrases=self.phrases[:500], boost=HINT_BOOST)] if self.phrases else [],
            ),
            interim_results=True,
        )

    def _requests(self):
        from google.cloud import speech_v1 as sp

        while (chunk := self.audio.get()) is not None:
            yield sp.StreamingRecognizeRequest(audio_content=chunk)

    def _run(self) -> None:
        committed: list[str] = []
        try:
            for resp in _speech().streaming_recognize(config=self._config(), requests=self._requests()):
                interim = []
                for r in resp.results:
                    if not r.alternatives:
                        continue
                    (committed if r.is_final else interim).append(r.alternatives[0].transcript.strip())
                self.on_text(" ".join([*committed, *interim]).strip())
            self.on_done(None)
        except Exception as e:  # noqa: BLE001 - live view is optional; report and stop
            log.warning("live STT stream failed: %s", e)
            self.on_done(f"{type(e).__name__}")

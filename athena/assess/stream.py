"""Streaming speech-to-text for live follow-along (Cloud Speech-to-Text v2, model "long").

Chirp 3 streams only whole sentences; "long" streams word-level interim results for
ne-NP and en-US (probe 18 Oct), which is what a moving highlight needs. Final scoring
still uses Chirp 3 + hints on the full recording. Audio is relayed, never stored.

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
MODEL = "long"
SAMPLE_RATE = 16000
MAX_SECONDS = 180  # a story read takes under a minute; stream limit is 5 min
MAX_BYTES = SAMPLE_RATE * 2 * MAX_SECONDS

_client = None
_client_lock = threading.Lock()


def _speech():
    global _client
    with _client_lock:
        if _client is None:
            from google.cloud.speech_v2 import SpeechClient

            _client = SpeechClient(client_options=ClientOptions(api_endpoint="speech.googleapis.com"))
    return _client


class StreamSession:
    def __init__(self, language: str, on_text: Callable[[str], None], on_done: Callable[[str | None], None]) -> None:
        self.language = language
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

    def _requests(self):
        from google.cloud.speech_v2.types import cloud_speech as cs

        config = cs.StreamingRecognitionConfig(
            config=cs.RecognitionConfig(
                explicit_decoding_config=cs.ExplicitDecodingConfig(
                    encoding="LINEAR16", sample_rate_hertz=SAMPLE_RATE, audio_channel_count=1
                ),
                language_codes=[LANG_CODE[self.language]],
                model=MODEL,
            ),
            streaming_features=cs.StreamingRecognitionFeatures(interim_results=True),
        )
        recognizer = f"projects/{settings().google_cloud_project}/locations/global/recognizers/_"
        yield cs.StreamingRecognizeRequest(recognizer=recognizer, streaming_config=config)
        while (chunk := self.audio.get()) is not None:
            yield cs.StreamingRecognizeRequest(audio=chunk)

    def _run(self) -> None:
        committed: list[str] = []
        try:
            for resp in _speech().streaming_recognize(requests=self._requests()):
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

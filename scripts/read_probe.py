"""Read-aloud end to end with synthetic speech: TTS → WebM/Opus → POST /api/session/read.

Each case is a scripted reading (with deliberate errors) of a fixed story, sent with
and without STT phrase hints, to see what the pipeline catches. Synthetic adult-ish
speech, not children: a PLUMBING check, not accuracy.

Known limits (17 Oct): TTS is non-deterministic and often "fixes" scripted errors
(said "a ship" when asked for "a sip"; "घरमा" for the non-word "गरमा"). A MISS can
be the voice, not the pipeline. Accuracy needs human recordings (eval C).

  python scripts/read_probe.py
"""

import subprocess
import sys
from pathlib import Path

from fastapi.testclient import TestClient
from google.genai import types

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from athena.api import app  # noqa: E402
from athena.config import genai_client  # noqa: E402
from athena.models import GenerationResult, StoryPlan  # noqa: E402
from athena.store import store  # noqa: E402

TTS_MODEL = "gemini-3.8-flash-tts"

STORIES = {
    "ne": ["आमा र बिरालो घरमा छन्।", "बिरालो दूध पिउँछ।", "आमा हाँस्नुहुन्छ।"],
    "en": ["Sam sat in a ship.", "The ship is big."],
}
# (label, what the "child" says, expected non-correct outcomes as {word: outcome})
CASES = {
    "ne": [
        ("correct", "आमा र बिरालो घरमा छन्। बिरालो दूध पिउँछ। आमा हाँस्नुहुन्छ।", {}),
        # Real-word errors only. Synthetic speech (and STT) pull non-words like "गरमा" back to
        # real words, so phoneme-level child errors need human recordings (eval C).
        ("omit+swap", "आमा र घरमा छन्। कुकुर दूध पिउँछ। आमा हाँस्नुहुन्छ।", {"बिरालो": "omitted", "बिरालो#2": "substituted"}),
        # An unrelated word before the right one is an insertion, not a self-correction:
        # without prosody it is indistinguishable from an added word. Only near-misses self-correct.
        ("insert", "आमा र कुकुर... बिरालो घरमा छन्। बिरालो दूध पिउँछ। आमा हाँस्नुहुन्छ।", {}),
    ],
    "en": [
        ("correct", "Sam sat in a ship. The ship is big.", {}),
        ("sh→s", "Sam sat in a sip. The ship is big.", {"ship": "substituted"}),
    ],
}


def speak(text: str) -> bytes:
    r = genai_client().models.generate_content(
        model=TTS_MODEL, contents=text, config=types.GenerateContentConfig(response_modalities=["AUDIO"])
    )
    pcm = r.candidates[0].content.parts[0].inline_data.data
    # Raw 24 kHz 16-bit mono PCM (or WAV) → WebM/Opus, what MediaRecorder sends.
    fmt = ["-f", "s16le", "-ar", "24000", "-ac", "1"] if not pcm.startswith(b"RIFF") else []
    return subprocess.run(
        ["ffmpeg", "-loglevel", "error", *fmt, "-i", "pipe:0", "-c:a", "libopus", "-f", "webm", "pipe:1"],
        input=pcm,
        capture_output=True,
        check=True,
    ).stdout


def make_story(lang: str) -> str:
    sentences = STORIES[lang]
    plan = StoryPlan(language=lang, learner_name="Sam", theme="probe", target_units=[], word_bank=[], mastery=[])
    result = GenerationResult(
        plan=plan, attempts=[], outcome="first_pass", title="probe", sentences=sentences, scene="",
        units_used=[], first_pass_violations=0, final_violation_count=0, total_latency_ms=0,
    )
    learner = store.list_learners()[0].id
    return store.add_story(learner, lang, result).id


def main() -> int:
    client = TestClient(app)
    failures = 0
    for lang, cases in CASES.items():
        story_id = make_story(lang)
        for label, spoken, expected in cases:
            audio = speak(spoken)
            for hints in (True, False):
                r = client.post(
                    "/api/session/read",
                    data={"story_id": story_id, "duration_s": "10", "hints": str(hints).lower()},
                    files={"audio": ("read.webm", audio, "audio/webm")},
                )
                if r.status_code != 200:
                    print(f"FAIL {lang} {label} hints={hints}: HTTP {r.status_code} {r.text[:200]}")
                    failures += 1
                    continue
                d = r.json()
                got: dict[str, str] = {}
                for w in d["words"]:
                    if w["outcome"] != "correct":
                        key, n = w["expected"], 2
                        while key in got:  # repeated word: बिरालो, बिरालो#2, ...
                            key, n = f"{w['expected']}#{n}", n + 1
                        got[key] = w["outcome"]
                ok = got == expected
                failures += 0 if ok else 1
                print(
                    f"{'OK  ' if ok else 'MISS'} {lang} {label:<12} hints={str(hints):<5} {d['engine']:<14} "
                    f"{d['stt_ms']:>5}ms  heard: {d['transcript']}"
                )
                if not ok:
                    print(f"       expected {expected}  got {got}  units {d['unit_errors']}")
    print(f"READ PROBE {'SUCCESS' if not failures else 'FAILED'}: {failures} miss(es)")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())

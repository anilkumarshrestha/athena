"""Make Athena's music once with Lyria (Vertex AI), into frontend/public/music/<id>.mp3.

  .venv/bin/python scripts/make_music.py            # only the missing ones
  .venv/bin/python scripts/make_music.py --redo star

Lyria makes ~30 s instrumental clips from a text prompt. Jingles are trimmed to a few seconds
with a fade; beds loop quietly under an activity. Shipped as static files: no music model call
while children use the app. Uses the gcloud login (Lyria runs in us-central1).
"""

import argparse
import base64
import json
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "frontend" / "public" / "music"
LOCATION, MODEL = "us-central1", "lyria-002"
NEGATIVE = "vocals, singing, speech, harsh, loud drums, distortion, scary, sad"

# id -> (prompt, seconds kept: None = whole clip as a loop)
TRACKS: dict[str, tuple[str, float | None]] = {
    "star": ("A very short, bright, joyful celebration fanfare for a child earning a star: glockenspiel and xylophone "
             "rising arpeggio, sparkly bells, happy and warm", 4.0),
    "story_done": ("A short happy flourish for a young child who just finished reading a story: ukulele strum, "
                   "hand claps and a cheerful marimba melody", 4.0),
    "cat": ("A short playful, quirky tune for a funny cartoon cat being thankful: pizzicato strings, wood block "
            "and a little slide whistle, cheerful", 3.5),
    "clap_bed": ("A steady, simple, gentle groove for a children's clapping game: soft hand drum and marimba, "
                 "90 bpm, clear even beat, light and friendly, loopable", None),
    "readalong": ("Very soft, calm background music for reading a picture book aloud to a young child: music box, "
                  "warm acoustic guitar, slow and gentle, no percussion, loopable", None),
}


def lyria(prompt: str, seed: int) -> bytes:
    project = subprocess.run(["gcloud", "config", "get-value", "project"], capture_output=True, text=True).stdout.strip()
    token = subprocess.run(["gcloud", "auth", "print-access-token"], capture_output=True, text=True).stdout.strip()
    url = (f"https://{LOCATION}-aiplatform.googleapis.com/v1/projects/{project}/locations/{LOCATION}"
           f"/publishers/google/models/{MODEL}:predict")
    body = {"instances": [{"prompt": prompt, "negative_prompt": NEGATIVE, "seed": seed}], "parameters": {}}
    req = urllib.request.Request(url, json.dumps(body).encode(),
                                 {"Authorization": f"Bearer {token}", "Content-Type": "application/json"})
    r = json.load(urllib.request.urlopen(req, timeout=240))
    return base64.b64decode(r["predictions"][0]["bytesBase64Encoded"])


def to_mp3(wav: bytes, seconds: float | None, out: Path) -> None:
    """Jingle: the first `seconds` with a short fade-out. Loop: whole clip, gentle fades so it loops softly."""
    if seconds:
        af = f"atrim=0:{seconds},afade=t=in:d=0.05,afade=t=out:st={seconds - 0.9}:d=0.9,loudnorm=I=-16:TP=-1.5"
    else:
        af = "afade=t=in:d=1.5,areverse,afade=t=in:d=1.5,areverse,loudnorm=I=-24:TP=-3"
    subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-i", "pipe:0", "-af", af, "-ac", "2", "-ar", "44100",
                    "-codec:a", "libmp3lame", "-b:a", "96k", str(out)], input=wav, check=True)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--redo", nargs="*", default=[])
    args = ap.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    for i, (tid, (prompt, seconds)) in enumerate(TRACKS.items()):
        path = OUT / f"{tid}.mp3"
        if path.exists() and tid not in args.redo:
            continue
        for attempt in range(4):
            try:
                t0 = time.time()
                to_mp3(lyria(prompt, seed=11 + i), seconds, path)
                print(f"{tid}: {path.stat().st_size // 1024} KB in {time.time() - t0:.0f}s", flush=True)
                break
            except Exception as e:  # noqa: BLE001 - quota or a blip: wait and retry
                print(f"  {tid}: {type(e).__name__} {str(e)[:120]}, retry", flush=True)
                time.sleep(20 * (attempt + 1))
    print("done:", ", ".join(sorted(p.stem for p in OUT.glob("*.mp3"))))


if __name__ == "__main__":
    main()

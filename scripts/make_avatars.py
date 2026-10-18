"""Draw the children's avatar characters once, into frontend/public/avatars/<id>.jpg.

  .venv/bin/python scripts/make_avatars.py            # draws only the missing ones
  .venv/bin/python scripts/make_avatars.py --redo fox # draw one again

Static files shipped with the app: no image calls while children use it, no quota surprises.
One shared character style so the set looks like a family (cf. athena/agents/illustrator.py).
"""

import argparse
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from google.genai import types  # noqa: E402

from athena.config import genai_client, settings  # noqa: E402

OUT = ROOT / "frontend" / "public" / "avatars"

# id -> (what to draw, background colour): pastel backgrounds from the app palette, varied
CHARACTERS: dict[str, tuple[str, str]] = {
    "unicorn": ("a white unicorn with a rainbow mane and a little golden horn", "#FFE1E1"),
    "frog": ("a bright green frog with big round eyes", "#DDF6E0"),
    "panda": ("a giant panda with black eye patches", "#EAF6FF"),
    "fox": ("an orange fox with a white-tipped tail", "#FFF1B8"),
    "red_panda": ("a red panda with a striped ringed tail and white face markings", "#FFE1E1"),
    "crocodile": ("a friendly green crocodile with a big toothless grin", "#DDF6E0"),
    "gorilla": ("a gentle grey-black gorilla", "#EAF6FF"),
    "whale": ("a happy blue whale with a little water spout", "#D6F3F7"),
    "tiger": ("a cheerful orange tiger cub with black stripes", "#FFF1B8"),
    "hippo": ("a round purple-grey hippo", "#EAF6FF"),
    "octopus": ("a pink octopus waving two of its arms", "#FFE1E1"),
    "rabbit": ("a white rabbit with long pink ears", "#DDF6E0"),
    "hen": ("a plump red-brown hen with a red comb", "#FFF1B8"),
    "monkey": ("a brown monkey with a light tan face", "#D6F3F7"),
    "giraffe": ("a yellow giraffe with brown spots and little horns", "#EAF6FF"),
}

STYLE = (
    "Avatar character for a children's reading app, in the spirit of Duolingo ABC and Cocomelon. "
    "Head and shoulders, facing the viewer, centred, filling most of a square frame so it can be "
    "cropped to a circle. Big friendly eyes, a happy smile, cute and gentle, never scary. Bright "
    "flat vector illustration, vivid saturated colours, thick rounded deep navy (#1E2A4A) outlines, "
    "big simple rounded shapes, no gradients. Plain solid background colour {bg}, nothing else in "
    "the picture. NO text, no letters, no logos."
)

SIZE = 512


def shrink(data: bytes) -> bytes:
    """Model PNG (~1 MB) -> 512 px JPEG (~40 KB)."""
    return subprocess.run(
        ["ffmpeg", "-loglevel", "error", "-i", "pipe:0", "-vf", f"scale={SIZE}:-1", "-q:v", "3", "-f", "mjpeg", "pipe:1"],
        input=data, capture_output=True, check=True, timeout=30,
    ).stdout


def draw(cid: str, what: str, bg: str) -> bytes:
    for attempt in range(5):
        try:
            r = genai_client("image").models.generate_content(
                model=settings().image_model,
                contents=f"Draw {what}.\n\n{STYLE.format(bg=bg)}",
                config=types.GenerateContentConfig(
                    response_modalities=["IMAGE"], image_config=types.ImageConfig(aspect_ratio="1:1")
                ),
            )
            for part in r.candidates[0].content.parts:
                if part.inline_data and part.inline_data.data:
                    return shrink(part.inline_data.data)
            raise RuntimeError("no image returned")
        except Exception as e:  # noqa: BLE001 - quota (429) or a blip: wait and retry
            wait = 20 * (attempt + 1)
            print(f"  {cid}: {type(e).__name__}, retry in {wait}s", flush=True)
            time.sleep(wait)
    raise RuntimeError(f"{cid}: gave up")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--redo", nargs="*", default=[], help="character ids to draw again")
    args = ap.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    for cid, (what, bg) in CHARACTERS.items():
        path = OUT / f"{cid}.jpg"
        if path.exists() and cid not in args.redo:
            continue
        t0 = time.time()
        path.write_bytes(draw(cid, what, bg))
        print(f"{cid}: {path.stat().st_size // 1024} KB in {time.time() - t0:.0f}s", flush=True)
        time.sleep(3)  # gentle on the image quota
    print("done:", ", ".join(sorted(p.stem for p in OUT.glob("*.jpg"))))


if __name__ == "__main__":
    main()

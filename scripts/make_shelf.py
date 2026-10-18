"""Write the shelf of ready-made stories for the demo children, into data/shelf/.

  .venv/bin/python scripts/make_shelf.py            # 4 stories per demo child and language
  .venv/bin/python scripts/make_shelf.py --n 6

Same pipeline as the app (planner -> writer -> verifier -> safety, picture in parallel), at
each demo child's demo levels (athena/demo.py), so the app's prepared-story check accepts them.
Only stories the model wrote and the verifier passed (first draft or rewritten) are kept: the
shelf is what a judge sees first. Pictures are shrunk to 800 px JPEG.
"""

import argparse
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from athena import api  # noqa: E402
from athena.demo import PLANS  # noqa: E402
from athena.shelf import SHELF  # noqa: E402
from athena.store import learner_from_dict, learner_to_dict, store  # noqa: E402


def shrink(data: bytes) -> bytes:
    return subprocess.run(["ffmpeg", "-loglevel", "error", "-i", "pipe:0", "-vf", "scale=800:-1", "-q:v", "4",
                           "-f", "mjpeg", "pipe:1"], input=data, capture_output=True, check=True).stdout


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=4)
    args = ap.parse_args()
    SHELF.mkdir(parents=True, exist_ok=True)
    for tid in ("sita", "ram", "leo"):
        t = store.learners[tid]
        child = learner_from_dict(learner_to_dict(t))  # a working copy at the demo levels
        plan = PLANS.get(child.name["en"], PLANS["Sita"])
        child.level = dict(plan["level"])
        langs = {"en": ["en"], "ne": ["ne"]}.get(child.profile.get("languages", "both"), ["ne", "en"])
        for lang in langs:
            out, titles, tries = [], set(), 0
            while len(out) < args.n and tries < args.n * 4:
                tries += 1
                result, image = api._compose(child, lang, None, "loop", 60)
                if result.outcome not in ("first_pass", "regenerated") or result.title in titles:
                    print(f"  {tid}/{lang}: skip ({result.outcome})", flush=True)
                    continue
                try:
                    data, _mime, _usage, _ms = image.result(timeout=240)
                except Exception as e:  # noqa: BLE001 - no picture: try another story
                    print(f"  {tid}/{lang}: picture failed ({type(e).__name__})", flush=True)
                    continue
                k = len(out)
                fn = f"{tid}_{lang}_{k}.jpg"
                (SHELF / fn).write_bytes(shrink(data))
                titles.add(result.title)
                out.append({"result": json.loads(result.model_dump_json()), "image": fn})
                print(f"{tid}/{lang} {k}: {result.title} ({result.outcome})", flush=True)
            (SHELF / f"{tid}_{lang}.json").write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    print("done")


if __name__ == "__main__":
    main()

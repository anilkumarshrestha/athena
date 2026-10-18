"""A shelf of ready-made stories for the demo children (Sita, Ram, Leo).

A visitor's first stories should appear at once, even on a cold Cloud Run instance. The shelf is
written ahead by scripts/make_shelf.py with the same planner -> writer -> verifier -> safety
pipeline and the story's picture, and shipped in data/shelf/. A shelf story goes into the
child's "prepared next story" slot (athena/api.py), which re-checks it against the child's
CURRENT letters and level before serving it, exactly like a story prepared in the background.

  data/shelf/<template>_<lang>.json   [{"result": GenerationResult, "image": "<file>.jpg"}]
  data/shelf/<file>.jpg               the picture (shrunk, ~80 KB)
"""

import json
import threading
from concurrent.futures import Future
from functools import lru_cache
from pathlib import Path

from athena.models import GenerationResult, Usage

SHELF = Path(__file__).resolve().parent.parent / "data" / "shelf"

_used: dict[tuple[str, str], int] = {}  # (learner, lang) -> stories taken from the shelf
_lock = threading.Lock()


@lru_cache
def _load(template: str, language: str) -> list[dict]:
    path = SHELF / f"{template}_{language}.json"
    if not path.exists():
        return []
    return json.loads(path.read_text(encoding="utf-8"))


def take(learner, language: str):
    """(GenerationResult, image Future) for a demo child's next shelf story, or None."""
    template = learner.profile.get("demo_of")
    if not template and learner.profile.get("demo_copy"):  # copies made before demo_of existed
        template = {"Sita": "sita", "Ram": "ram", "Leo": "leo"}.get(learner.name.get("en", ""))
    if not template:
        return None
    items = _load(template, language)
    with _lock:
        k = _used.get((learner.id, language), 0)
        if k >= len(items):
            return None
        _used[(learner.id, language)] = k + 1
    item = items[k]
    result = GenerationResult.model_validate(item["result"])
    image: Future = Future()
    pic = SHELF / item["image"] if item.get("image") else None
    if pic and pic.exists():
        image.set_result((pic.read_bytes(), "image/jpeg", Usage(model="shelf"), 0))
    else:
        image.set_exception(RuntimeError("no shelf picture"))
    return result, image

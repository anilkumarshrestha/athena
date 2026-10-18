"""Story + reading history per learner: an append-only JSONL file of events.

  state/stories/<learner_id>.jsonl
    {"type": "story",   "story_id", "at", "lang", "title", "sentences", "theme", "level", "outcome", "units_used", "attempts"}
    {"type": "image",   "story_id", "image_id"}
    {"type": "reading", "story_id", "at", "transcript", "engine", "wcpm", "words_correct", "words", "insertions"}
    {"type": "close",   "story_id", "at", "accuracy", "level_before", "level_after", "changes"}
    {"type": "reteach", "story_id", "at", "index", "word", "styles", "correct"}   see athena/reteach.py
    {"type": "maths", ...} / {"type": "maths_answer", ...}   see athena/maths_progress.py

Append-only: a crash can lose at most the last line, never earlier history. No audio is
ever stored (PLAN §11). "transcript" is what speech-to-text heard from the child reading
a known story: child data, so the file is git-ignored and deleted with the learner.
"""

import json
import re
import threading
from pathlib import Path

_ID = re.compile(r"^[0-9a-zA-Z_-]{1,64}$")


class History:
    def __init__(self, base: Path | None) -> None:
        self.base = base  # None: disabled (tests)
        self._lock = threading.Lock()

    def _path(self, learner_id: str) -> Path | None:
        if not self.base or not _ID.match(learner_id):  # id validated: no path traversal
            return None
        return self.base / f"{learner_id}.jsonl"

    def append(self, learner_id: str, event: dict) -> None:
        path = self._path(learner_id)
        if not path:
            return
        line = json.dumps(event, ensure_ascii=False)
        with self._lock:
            path.parent.mkdir(parents=True, exist_ok=True)
            with path.open("a", encoding="utf-8") as f:
                f.write(line + "\n")

    def _events(self, learner_id: str) -> list[dict]:
        path = self._path(learner_id)
        if not path or not path.exists():
            return []
        out = []
        for raw in path.read_text(encoding="utf-8").splitlines():
            try:
                out.append(json.loads(raw))
            except json.JSONDecodeError:
                continue  # a torn last line after a crash
        return out

    def stories(self, learner_id: str) -> list[dict]:
        """Story records with their readings and outcome, newest first."""
        return fold(self._events(learner_id))

    def events(self, learner_id: str) -> list[dict]:
        """All events in write order (for rebuilding an open activity after a restart)."""
        return self._events(learner_id)

    def maths(self, learner_id: str) -> list[dict]:
        """Maths problems with the child's answers, newest first."""
        from athena.maths_progress import fold_maths

        return fold_maths(self._events(learner_id))

    def story(self, learner_id: str, story_id: str) -> dict | None:
        return next((r for r in self.stories(learner_id) if r["story_id"] == story_id), None)

    def delete(self, learner_id: str) -> None:
        path = self._path(learner_id)
        if path and path.exists():
            path.unlink()


def fold(events: list[dict]) -> list[dict]:
    """Events (in write order) -> story records with readings and close, newest first."""
    records: dict[str, dict] = {}
    for e in events:
        sid = e.get("story_id")
        if e.get("type") == "story":
            records[sid] = {**e, "image_id": None, "readings": [], "close": None, "reteach": []}
        elif sid in records:
            r = records[sid]
            if e["type"] == "image":
                r["image_id"] = e.get("image_id")
            elif e["type"] == "reading":
                r["readings"].append(e)
            elif e["type"] == "close":
                r["close"] = e
            elif e["type"] == "reteach":
                r["reteach"].append(e)
    return sorted(records.values(), key=lambda r: r["at"], reverse=True)

"""Learner + story store.

Learners are persisted to a JSON file (state_dir/learners.json), written atomically after
every change and loaded at startup, so a restart keeps every child's profile and progress.
Stories stay in memory: they are per-session. The file holds children's first names and
progress: it is git-ignored and learners can be deleted on request.
Cloud Run disk is ephemeral; move to Firestore when deployed beyond one instance.
"""

import json
import os
import threading
import time
import uuid
from dataclasses import dataclass, field
from dataclasses import asdict
from pathlib import Path
from typing import Literal

from athena.history import History
from athena.mastery import UnitState, allowed
from athena.models import GenerationResult, Language
from athena.presets import preset

ImageStatus = Literal["pending", "ready", "failed"]


@dataclass
class Learner:
    id: str
    name: dict[str, str]  # per language: {"ne": "सीता", "en": "Sita"}
    avatar: str
    units: dict[str, dict[str, UnitState]]  # per language: signature -> state
    profile: dict[str, str] = field(default_factory=dict)  # favorite_animal, favorite_food, setting (fixed ids)
    level: dict[str, int] = field(default_factory=lambda: {"ne": 1, "en": 1})  # story shape band
    history: dict[str, list[float]] = field(default_factory=lambda: {"ne": [], "en": []})  # accuracy per session
    sessions: list[dict] = field(default_factory=list)  # closed reading sessions (athena/dashboard.py)
    settings: dict[str, int] = field(default_factory=lambda: {"daily_minutes": 0})  # parent controls; 0 = no limit

    @property
    def mastery(self) -> dict[str, frozenset[str]]:
        """Signatures stories may use now, per language (mastered + active practicing)."""
        return {lang: allowed(u) for lang, u in self.units.items()}


@dataclass
class Story:
    id: str
    learner_id: str
    language: Language
    result: GenerationResult
    image_status: ImageStatus = "pending"
    image_id: str | None = None
    image_latency_ms: int | None = None
    readings: list = field(default_factory=list)  # Assessment per read-aloud attempt (no audio kept)
    changes: list | None = None  # mastery Changes once the session is closed
    created_at: float = field(default_factory=time.time)


def learner_to_dict(learner: Learner) -> dict:
    return asdict(learner)


def learner_from_dict(d: dict) -> Learner:
    return Learner(
        id=d["id"],
        name=d["name"],
        avatar=d.get("avatar", ""),
        units={lang: {sig: UnitState(**u) for sig, u in units.items()} for lang, units in d["units"].items()},
        profile=d.get("profile", {}),
        level=d.get("level", {"ne": 1, "en": 1}),
        history=d.get("history", {"ne": [], "en": []}),
        sessions=d.get("sessions", []),
        settings=d.get("settings", {"daily_minutes": 0}),
    )


class MemoryStore:
    def __init__(self, path: Path | None = None, history: History | None = None) -> None:
        self._lock = threading.RLock()
        self.path = path  # None: memory only (tests)
        self.history = history or History(None)  # story + reading events per learner
        self.learners: dict[str, Learner] = {}
        self.stories: dict[str, Story] = {}

    def load(self) -> bool:
        """Load learners from disk. False if there is no file yet."""
        if not self.path or not self.path.exists():
            return False
        data = json.loads(self.path.read_text(encoding="utf-8"))
        with self._lock:
            self.learners = {d["id"]: learner_from_dict(d) for d in data["learners"]}
        return True

    def save(self) -> None:
        """Write all learners atomically: temp file, then rename (no half-written file)."""
        if not self.path:
            return
        with self._lock:
            payload = {"version": 1, "learners": [learner_to_dict(x) for x in self.learners.values()]}
            self.path.parent.mkdir(parents=True, exist_ok=True)
            tmp = self.path.with_suffix(".tmp")
            tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=1), encoding="utf-8")
            os.replace(tmp, self.path)

    def delete_learner(self, learner_id: str) -> bool:
        with self._lock:
            gone = self.learners.pop(learner_id, None) is not None
            self.stories = {k: v for k, v in self.stories.items() if v.learner_id != learner_id}
        if gone:
            self.save()
            self.history.delete(learner_id)  # their stories and readings go too
        return gone

    def list_learners(self) -> list[Learner]:
        return list(self.learners.values())

    def get_learner(self, learner_id: str) -> Learner | None:
        return self.learners.get(learner_id)

    def put_learner(self, learner: Learner) -> None:
        with self._lock:
            self.learners[learner.id] = learner
        self.save()

    def add_story(self, learner_id: str, language: Language, result: GenerationResult) -> Story:
        story = Story(id=uuid.uuid4().hex[:12], learner_id=learner_id, language=language, result=result)
        with self._lock:
            self.stories[story.id] = story
        return story

    def get_story(self, story_id: str) -> Story | None:
        return self.stories.get(story_id)

    def set_image(self, story_id: str, status: ImageStatus, image_id: str | None, latency_ms: int | None) -> None:
        with self._lock:
            s = self.stories.get(story_id)
            if s:
                s.image_status, s.image_id, s.image_latency_ms = status, image_id, latency_ms


def _seed(store: MemoryStore) -> None:
    for lid, names, avatar, ne, ne_p, en, en_p in [
        # preset = mastered units; then a few units the learner is practising
        ("sita", {"ne": "सीता", "en": "Sita"}, "goat", "ne_basic", ["c:ड", "m:ै"], "en_satpin_sh", ["g:m", "g:d"]),
        ("ram", {"ne": "राम", "en": "Ram"}, "yak", "ne_mid", ["k:क्ष", "k:न्छ"], "en_p3", ["g:ay", "g:ou"]),
    ]:
        units = {}
        for lang, preset_name, practicing in (("ne", ne, ne_p), ("en", en, en_p)):
            u = {sig: UnitState("mastered", streak=3, seen=3) for sig in preset(preset_name)[1]}
            u.update({sig: UnitState("practicing", streak=0, seen=1) for sig in practicing})
            units[lang] = u
        level = {"sita": {"ne": 1, "en": 1}, "ram": {"ne": 2, "en": 2}}[lid]
        profile = {
            "sita": {"favorite_animal": "goat", "favorite_food": "dal_bhat", "setting": "hills"},
            "ram": {"favorite_animal": "yak", "favorite_food": "momo", "setting": "mountains"},
        }[lid]
        store.put_learner(Learner(id=lid, name=names, avatar=avatar, units=units, level=level, profile=profile))


def new_learner(name_ne: str, name_en: str, profile: dict[str, str], start: str) -> Learner:
    from athena.profile import STARTS  # lazy: profile imports the planner

    ne_preset, en_preset, level = STARTS[start]
    units = {
        lang: {sig: UnitState("mastered", streak=3, seen=3) for sig in preset(p)[1]}
        for lang, p in (("ne", ne_preset), ("en", en_preset))
    }
    return Learner(
        id=uuid.uuid4().hex[:8],
        name={"ne": name_ne, "en": name_en},
        avatar=profile.get("favorite_animal", ""),
        units=units,
        level={"ne": level, "en": level},
        profile=profile,
    )


def _open_store() -> MemoryStore:
    from athena.config import settings

    state = Path(settings().state_dir)
    st = MemoryStore(state / "learners.json", History(state / "stories"))
    if not st.load():
        _seed(st)  # first run: demo learners, written to disk
    return st


store = _open_store()

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
import logging
import uuid
from dataclasses import dataclass, field
from dataclasses import asdict
from pathlib import Path
from typing import Literal

from athena import family as families
from athena.history import History
from athena.mastery import UnitState, allowed
from athena.models import GenerationResult, Language
from athena.presets import preset

log = logging.getLogger("athena")

ImageStatus = Literal["pending", "ready", "failed", "off"]  # off: parent turned story pictures off


DEFAULT_CONTROLS = {"maths": True, "teach": True, "pictures": True, "avoid_themes": []}


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
    # parent content controls: activities on/off, story pictures, themes to avoid (fixed list)
    controls: dict = field(default_factory=lambda: dict(DEFAULT_CONTROLS))
    family: str = ""  # who may see this child (athena/family.py); "" = not assigned yet
    # maths difficulty, per language, separate from reading (athena/maths_progress.py)
    maths: dict[str, dict] = field(default_factory=lambda: {"ne": {"level": 1, "recent": []}, "en": {"level": 1, "recent": []}})

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
        maths=d.get("maths", {"ne": {"level": 1, "recent": []}, "en": {"level": 1, "recent": []}}),
        controls={**DEFAULT_CONTROLS, **d.get("controls", {})},
        family=d.get("family", ""),
    )


class MemoryStore:
    def __init__(self, path: Path | None = None, history: History | None = None) -> None:
        self._lock = threading.RLock()
        self.path = path  # None: memory only (tests)
        self.history = history or History(None)  # story + reading events per learner
        self.learners: dict[str, Learner] = {}
        self.stories: dict[str, Story] = {}
        self.accounts: dict[str, dict] = {}  # Google account id (sub) -> {"family", "email"}

    def _accounts_path(self) -> Path | None:
        return self.path.parent / "accounts.json" if self.path else None

    def get_account(self, sub: str) -> dict | None:
        return self.accounts.get(sub)

    def put_account(self, sub: str, data: dict) -> None:
        with self._lock:
            self.accounts[sub] = data
            path = self._accounts_path()
            if path:
                tmp = path.with_suffix(".tmp")
                tmp.write_text(json.dumps(self.accounts, ensure_ascii=False), encoding="utf-8")
                os.replace(tmp, path)

    def account_for_family(self, fid: str) -> dict | None:
        return next((a for a in self.accounts.values() if a.get("family") == fid), None)

    def move_family(self, src: str, dst: str) -> None:
        """Signing in to an account that already has a family: this browser's own children move
        into it; its untouched demo copies are dropped (the account already has its own)."""
        with self._lock:
            for x in list(self.learners.values()):
                if x.family != src:
                    continue
                if x.profile.get("demo_copy") and all(s.get("demo") for s in x.sessions):  # only sample sessions
                    self.learners.pop(x.id)
                else:
                    x.family = dst
        self.save()

    def load(self) -> bool:
        """Load learners from disk. False if there is no file yet."""
        if (ap := self._accounts_path()) and ap.exists():
            self.accounts = json.loads(ap.read_text(encoding="utf-8"))
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
        if self.get_learner(learner_id) is None:  # unknown, or another family's child
            return False
        with self._lock:
            gone = self.learners.pop(learner_id, None) is not None
            self.stories = {k: v for k, v in self.stories.items() if v.learner_id != learner_id}
        if gone:
            self.save()
            self.history.delete(learner_id)  # their stories and readings go too
        return gone

    def list_learners(self) -> list[Learner]:
        """The current family's children (all of them outside a request: background work)."""
        fam = families.current.get()
        return [x for x in self.learners.values() if fam is None or x.family == fam]

    def get_learner(self, learner_id: str) -> Learner | None:
        """None for another family's child: every endpoint then answers 404 (athena/family.py)."""
        x = self.learners.get(learner_id)
        fam = families.current.get()
        return x if x is not None and (fam is None or x.family == fam) else None

    def put_learner(self, learner: Learner) -> None:
        if not learner.family and (fam := families.current.get()):
            learner.family = fam
        with self._lock:
            self.learners[learner.id] = learner
        self.save()

    def family_learners(self, fid: str) -> list[Learner]:
        return [x for x in self.learners.values() if x.family == fid]

    def ensure_family(self) -> list[Learner]:
        """A new family starts with its own copies of the demo children (Sita, Ram)."""
        fam = families.current.get()
        if fam is None:
            return self.list_learners()
        mine = self.family_learners(fam)
        if mine:
            return mine
        copies = []
        for t in self.family_learners(families.DEMO):
            # same letters and level as the demo child; their own fresh history
            c = learner_from_dict({**learner_to_dict(t), "id": uuid.uuid4().hex[:8], "family": fam,
                                   "sessions": [], "history": {"ne": [], "en": []},
                                   "profile": {**t.profile, "demo_copy": "1"}})
            copies.append(c)
        from athena.demo import sample_week

        weeks = {}
        for c in copies:  # a lived-in sample week, so the parent view has something to show
            try:
                sessions, events, over = sample_week(c)
            except Exception:  # noqa: BLE001 - an empty demo child is still usable
                log.exception("sample week failed for %s", c.name.get("en"))
                continue
            c.sessions, c.level, c.maths, c.history = sessions, over["level"], over["maths"], over["history"]
            weeks[c.id] = events
        with self._lock:
            for c in copies:
                self.learners[c.id] = c
        self.save()
        for lid, events in weeks.items():
            self.history.append_many(lid, events)
        return copies

    def adopt_unassigned(self) -> None:
        """Learners from before families: the demo templates, and the rest into the legacy family."""
        legacy = None
        with self._lock:
            for x in self.learners.values():
                if x.family:
                    continue
                if x.id in DEMO_IDS:
                    x.family = families.DEMO
                else:
                    legacy = legacy or families.legacy_family()
                    x.family = legacy
        if legacy:
            self.save()
            log.warning("learners from before families are in family code %s", families.pretty(legacy))

    def get_story(self, story_id: str) -> Story | None:
        s = self.stories.get(story_id)
        return s if s is not None and self.get_learner(s.learner_id) is not None else None

    def add_story(self, learner_id: str, language: Language, result: GenerationResult) -> Story:
        story = Story(id=uuid.uuid4().hex[:12], learner_id=learner_id, language=language, result=result)
        with self._lock:
            self.stories[story.id] = story
        return story

    def set_image(self, story_id: str, status: ImageStatus, image_id: str | None, latency_ms: int | None) -> None:
        with self._lock:
            s = self.stories.get(story_id)
            if s:
                s.image_status, s.image_id, s.image_latency_ms = status, image_id, latency_ms


DEMO_IDS = ("sita", "ram", "leo")

# Demo children (templates, family DEMO): each new family gets its own copies with a sample
# week (athena/demo.py). Leo learns English only, for visitors who do not read Nepali.
# preset = mastered units; then a few units the learner is practising.
_DEMOS = [
    ("sita", {"ne": "सीता", "en": "Sita"}, None, "ne_basic", ["c:ड", "m:ै"], "en_satpin_sh", ["g:m", "g:d"],
     {"ne": 1, "en": 1}, {"favorite_animal": "goat", "favorite_food": "dal_bhat", "setting": "hills", "gender": "girl"}),
    ("ram", {"ne": "राम", "en": "Ram"}, None, "ne_mid", ["k:क्ष", "k:न्छ"], "en_p3", ["g:ay", "g:ou"],
     {"ne": 2, "en": 2}, {"favorite_animal": "yak", "favorite_food": "momo", "setting": "mountains", "gender": "boy"}),
    ("leo", {"ne": "लियो", "en": "Leo"}, "fox", "ne_early", [], "en_p3", ["g:igh", "g:oa"],
     {"ne": 1, "en": 2}, {"favorite_animal": "dog", "favorite_food": "egg", "setting": "city", "gender": "boy",
                          "languages": "en", "buddy": "dog", "activity": "football"}),
]


def _seed(store: MemoryStore) -> None:
    """Add any demo child the store does not have yet (new databases, and Leo on old ones)."""
    for lid, names, avatar, ne, ne_p, en, en_p, level, profile in _DEMOS:
        if lid in store.learners:
            continue
        units = {}
        for lang, preset_name, practicing in (("ne", ne, ne_p), ("en", en, en_p)):
            u = {sig: UnitState("mastered", streak=3, seen=3) for sig in preset(preset_name)[1]}
            u.update({sig: UnitState("practicing", streak=0, seen=1) for sig in practicing})
            units[lang] = u
        store.put_learner(Learner(id=lid, name=names, avatar=avatar or "", units=units, level=dict(level),
                                  profile=dict(profile), family=families.DEMO))


def new_learner(name_ne: str, name_en: str, profile: dict[str, str], start: str) -> Learner:
    from athena.profile import STARTS  # lazy: profile imports the planner

    ne_preset, en_preset, level = STARTS[start]
    if profile.get("age") in ("4", "5"):
        level = 1  # youngest readers start with the shortest stories (the card check refines units)
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

    s = settings()
    if s.store_backend == "firestore":
        from athena.firestore_store import open_firestore_store

        st = open_firestore_store(s.firestore_prefix)
        _seed(st)  # empty database: demo learners; older ones: any missing demo child
        st.adopt_unassigned()
        return st
    state = Path(s.state_dir)
    st = MemoryStore(state / "learners.json", History(state / "stories"))
    st.load()
    _seed(st)  # first run: demo learners; later: any missing demo child
    st.adopt_unassigned()
    return st


store = _open_store()

"""Learner + story store. In-memory for now (Cloud Run max-instances=1); Firestore later."""

import threading
import time
import uuid
from dataclasses import dataclass, field
from typing import Literal

from athena.models import GenerationResult, Language
from athena.presets import preset

ImageStatus = Literal["pending", "ready", "failed"]


@dataclass
class Learner:
    id: str
    name: dict[str, str]  # per language: {"ne": "सीता", "en": "Sita"}
    avatar: str
    mastery: dict[str, set[str]]


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
    created_at: float = field(default_factory=time.time)


class MemoryStore:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self.learners: dict[str, Learner] = {}
        self.stories: dict[str, Story] = {}

    def list_learners(self) -> list[Learner]:
        return list(self.learners.values())

    def get_learner(self, learner_id: str) -> Learner | None:
        return self.learners.get(learner_id)

    def put_learner(self, learner: Learner) -> None:
        with self._lock:
            self.learners[learner.id] = learner

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
    for lid, names, avatar, ne, en in [
        ("sita", {"ne": "सीता", "en": "Sita"}, "goat", "ne_basic", "en_satpin_sh"),
        ("ram", {"ne": "राम", "en": "Ram"}, "yak", "ne_mid", "en_p3"),
    ]:
        store.put_learner(
            Learner(
                id=lid,
                name=names,
                avatar=avatar,
                mastery={"ne": set(preset(ne)[1]), "en": set(preset(en)[1])},
            )
        )


store = MemoryStore()
_seed(store)

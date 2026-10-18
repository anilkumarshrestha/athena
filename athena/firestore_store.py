"""Firestore persistence (STORE_BACKEND=firestore): learners and story history survive
restarts and scale-to-zero on Cloud Run.

  {prefix}learners/{learner_id}                 the learner (profile, units, level, sessions)
  {prefix}learners/{learner_id}/events/{auto}   story / image / reading / close events

Same interfaces as the file backend (athena/store.py, athena/history.py): the in-memory
learner dict stays the working copy; every save writes the changed learners through.
Deleting a learner deletes their events too. No audio is ever stored.
"""

import logging
import threading
import time

from athena.history import History, fold
from athena.store import MemoryStore, learner_from_dict, learner_to_dict

log = logging.getLogger("athena")


def _client():
    from google.cloud import firestore

    from athena.config import settings

    return firestore.Client(project=settings().google_cloud_project or None)


class FirestoreHistory(History):
    def __init__(self, db, prefix: str = "") -> None:
        super().__init__(None)
        self.db = db
        self.col = f"{prefix}learners"

    def _events_ref(self, learner_id: str):
        return self.db.collection(self.col).document(learner_id).collection("events")

    def append(self, learner_id: str, event: dict) -> None:
        try:
            self._events_ref(learner_id).add({**event, "ts": time.time()})
        except Exception:  # noqa: BLE001 - history is for review; never break the child's flow
            log.exception("history write failed")

    def _events(self, learner_id: str) -> list[dict]:
        docs = self._events_ref(learner_id).order_by("ts").stream()
        return [d.to_dict() for d in docs]

    def delete(self, learner_id: str) -> None:
        for d in self._events_ref(learner_id).stream():
            d.reference.delete()


class FirestoreStore(MemoryStore):
    def __init__(self, db, prefix: str = "") -> None:
        super().__init__(None, FirestoreHistory(db, prefix))
        self.db = db
        self.col = f"{prefix}learners"
        self._write_lock = threading.Lock()

    def load(self) -> bool:
        docs = list(self.db.collection(self.col).stream())
        with self._lock:
            self.learners = {d.id: learner_from_dict(d.to_dict()) for d in docs}
        return bool(docs)

    def save(self) -> None:
        """Write every learner through (a handful of documents; batched, atomic)."""
        with self._lock:
            payload = {lid: learner_to_dict(x) for lid, x in self.learners.items()}
        with self._write_lock:
            batch = self.db.batch()
            for lid, data in payload.items():
                batch.set(self.db.collection(self.col).document(lid), data)
            batch.commit()

    def delete_learner(self, learner_id: str) -> bool:
        with self._lock:
            gone = self.learners.pop(learner_id, None) is not None
            self.stories = {k: v for k, v in self.stories.items() if v.learner_id != learner_id}
        if gone:
            self.history.delete(learner_id)  # events first, then the learner document
            self.db.collection(self.col).document(learner_id).delete()
        return gone


def open_firestore_store(prefix: str = "") -> FirestoreStore:
    st = FirestoreStore(_client(), prefix)
    st.load()
    return st


__all__ = ["FirestoreHistory", "FirestoreStore", "fold", "open_firestore_store"]

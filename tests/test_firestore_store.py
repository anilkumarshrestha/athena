"""The Firestore store against an in-memory fake: the code path Cloud Run uses (local runs use files)."""

from athena import family
from athena.firestore_store import FirestoreStore
from athena.store import new_learner


class _Doc:
    def __init__(self, store, path):
        self.store, self.path = store, path

    def set(self, data):
        self.store[self.path] = data

    def delete(self):
        self.store.pop(self.path, None)

    def collection(self, name):
        return _Col(self.store, f"{self.path}/{name}")


class _Snap:
    def __init__(self, path, data):
        self.id, self._data = path.rsplit("/", 1)[1], data

    def to_dict(self):
        return dict(self._data)


class _Col:
    def __init__(self, store, path):
        self.store, self.path = store, path

    def document(self, doc_id):
        return _Doc(self.store, f"{self.path}/{doc_id}")

    def stream(self):
        return [_Snap(k, v) for k, v in self.store.items() if k.rsplit("/", 1)[0] == self.path]

    def add(self, data):
        self.store[f"{self.path}/{len(self.store)}"] = data

    def order_by(self, *_a, **_k):
        return self


class _Batch:
    def __init__(self):
        self.ops = []

    def set(self, doc, data):
        self.ops.append((doc, data))

    def commit(self):
        for doc, data in self.ops:
            doc.set(data)


class FakeDB:
    def __init__(self):
        self.data: dict[str, dict] = {}

    def collection(self, name):
        return _Col(self.data, name)

    def batch(self):
        return _Batch()


def test_firestore_store_loads_saves_and_keeps_accounts():
    db = FakeDB()
    st = FirestoreStore(db, "t_")
    assert st.load() is False  # empty database: no crash (the Cloud Run startup path)
    learner = new_learner("सीता", "Sita", {"favorite_animal": "cat"}, "beginner")
    learner.family = family.new_id()
    st.put_learner(learner)
    st.put_account("google-sub-1", {"family": learner.family, "email": "p@example.com"})
    assert f"t_learners/{learner.id}" in db.data and "t_accounts/google-sub-1" in db.data
    writes = len(db.data)
    st.save()  # nothing changed: nothing rewritten
    assert len(db.data) == writes

    again = FirestoreStore(db, "t_")  # a restart
    assert again.load() is True
    assert again.get_learner(learner.id).name["en"] == "Sita"
    assert again.get_account("google-sub-1")["family"] == learner.family

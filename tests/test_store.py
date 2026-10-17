"""Learner persistence: atomic JSON round trip and deletion. Uses a temp dir."""

import json

from athena.mastery import UnitState
from athena.store import Learner, MemoryStore


def learner(lid="a1"):
    return Learner(
        id=lid,
        name={"ne": "मीना", "en": "Mina"},
        avatar="hen",
        units={"ne": {"c:क": UnitState("mastered", 3, 3), "m:ु": UnitState("practicing", 1, 2, cooldown=1)}, "en": {}},
        profile={"favorite_animal": "hen"},
        level={"ne": 2, "en": 1},
        history={"ne": [0.9, 1.0], "en": []},
    )


def test_round_trip(tmp_path):
    path = tmp_path / "learners.json"
    a = MemoryStore(path)
    a.put_learner(learner())
    b = MemoryStore(path)
    assert b.load()
    got = b.get_learner("a1")
    assert got.name["ne"] == "मीना"
    assert got.units["ne"]["m:ु"] == UnitState("practicing", 1, 2, cooldown=1)
    assert got.level == {"ne": 2, "en": 1} and got.history["ne"] == [0.9, 1.0]
    assert "मीना" in path.read_text(encoding="utf-8")  # readable UTF-8, not escaped
    assert not path.with_suffix(".tmp").exists()  # atomic write left no temp file


def test_delete_removes_from_disk(tmp_path):
    path = tmp_path / "learners.json"
    s = MemoryStore(path)
    s.put_learner(learner("a1"))
    s.put_learner(learner("b2"))
    assert s.delete_learner("a1")
    assert [x["id"] for x in json.loads(path.read_text())["learners"]] == ["b2"]
    assert not s.delete_learner("a1")


def test_no_file_means_fresh_start(tmp_path):
    assert not MemoryStore(tmp_path / "none.json").load()

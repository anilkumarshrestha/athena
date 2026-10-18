"""Maths progress for parent/teacher views: folded from the child's taps. Temp dir."""

from athena.history import History
from athena.maths_progress import summarize_maths

NOW = 10 * 86400.0


def _problem(h, pid, at, a, b, op, answers, lang="ne"):
    h.append("k1", {"type": "maths", "story_id": pid, "at": at, "lang": lang, "sentences": ["?"],
                    "a": a, "b": b, "op": op, "source": "template"})
    right = a + b if op == "+" else a - b
    for i, x in enumerate(answers, 1):
        h.append("k1", {"type": "maths_answer", "story_id": pid, "at": at + i, "answer": x, "correct": x == right, "try": i})


def test_problems_fold_with_answers_and_mistake_kinds(tmp_path):
    h = History(tmp_path)
    _problem(h, "p1", NOW - 100, 3, 2, "+", [5])  # first try
    _problem(h, "p2", NOW - 90, 7, 3, "-", [10, 4])  # added instead of took away, then right
    _problem(h, "p3", NOW - 80, 4, 4, "+", [7, 9])  # off by one twice, not solved
    rs = h.maths("k1")
    assert [r["id"] for r in rs] == ["p3", "p2", "p1"]  # newest first
    p1, p2, p3 = rs[2], rs[1], rs[0]
    assert p1["first_try"] and p1["solved"] and p1["mistakes"] == []
    assert not p2["first_try"] and p2["solved"] and p2["mistakes"] == ["wrong_operation"]
    assert not p3["solved"] and p3["mistakes"] == ["off_by_one", "off_by_one"]
    assert h.stories("k1") == []  # maths events never show up as stories


def test_summary_counts_week_ops_and_struggles(tmp_path):
    h = History(tmp_path)
    for i in range(3):
        _problem(h, f"s{i}", NOW - 1000 - i, 6, 2, "-", [8, 4])  # subtraction keeps going wrong
    _problem(h, "a1", NOW - 500, 2, 2, "+", [4])
    _problem(h, "old", NOW - 30 * 86400, 1, 1, "+", [2])  # outside the week
    _problem(h, "skip", NOW - 10, 3, 1, "+", [])  # shown, never answered
    _problem(h, "en1", NOW - 10, 1, 2, "+", [3], lang="en")
    s = summarize_maths(h.maths("k1"), "ne", NOW)
    assert s["total"] == 6 and s["week"]["problems"] == 5 and s["week"]["answered"] == 4
    assert s["by_op"]["-"] == {"problems": 3, "first_try": 0.0}
    assert s["by_op"]["+"] == {"problems": 2, "first_try": 1.0}
    assert s["struggling"] == ["-"]
    assert s["mistakes"] == {"wrong_operation": 3}
    assert s["largest_solved"] == 4
    assert sum(s["week"]["per_day"]) == 5 and s["week"]["per_day"][-1] == 5
    assert s["recent"][0]["id"] == "skip" and s["recent"][0]["answers"] == []


# --- maths level, daily time, restart-safe answers --------------------------------------

from concurrent.futures import Future

import pytest

from athena.maths_progress import maths_seconds_today, next_maths_level


def test_maths_level_moves_on_first_tries():
    assert next_maths_level(1, [True, True, False, True, True]) == 2  # 4 of 5
    assert next_maths_level(1, [True, True, True, True]) == 1  # not enough yet
    assert next_maths_level(2, [True, False, False, False]) == 1  # 3 misses in a row
    assert next_maths_level(1, [False, False, False]) == 1  # floor
    assert next_maths_level(3, [True] * 5) == 3  # ceiling


def test_maths_time_counts_shown_to_last_tap_capped(tmp_path):
    h = History(tmp_path)
    _problem(h, "p1", NOW - 600, 2, 1, "+", [3])  # taps at +1 s and +60 s: 60 s
    _problem(h, "p2", NOW - 500, 2, 2, "+", [])  # skipped: 0
    h.append("k1", {"type": "maths_answer", "story_id": "p1", "at": NOW - 540, "answer": 3, "correct": True, "try": 2})
    _problem(h, "open", NOW - 400, 1, 1, "+", [])  # newest, unanswered: 400 s until now, capped at 180
    secs = maths_seconds_today(h.maths("k1"), NOW, lambda a, b: True)
    assert secs == 60 + 0 + 180


@pytest.fixture
def maths_api(tmp_path, monkeypatch, own):
    import athena.api as api
    import athena.maths as maths
    from athena.store import new_learner, store

    learner = new_learner("किरण", "Kiran", {}, next(iter(__import__("athena.profile", fromlist=["STARTS"]).STARTS)))
    learner.id = "ktest"
    monkeypatch.setattr(store, "history", History(tmp_path))
    monkeypatch.setattr(store, "save", lambda: None)
    monkeypatch.setitem(store.learners, learner.id, learner)

    def fixed(plan, seed=None, prefer=()):  # 2 + 1, no model call
        p = maths.Problem(plan.language, 2, 1, "+", "केरा", sentences=["२ केरा।", "१ केरा।", "कति केरा?"], source="template")
        return p

    done = Future()
    done.set_exception(RuntimeError("not prepared in tests"))
    monkeypatch.setattr(maths, "quick_problem", fixed)
    monkeypatch.setattr(maths, "make_problem", fixed)
    monkeypatch.setattr(api._pool, "submit", lambda *a, **k: done)
    from fastapi.testclient import TestClient

    client = TestClient(api.app)
    own(client, learner)
    yield client, api, learner


def test_answer_survives_restart_and_level_rises(maths_api):
    client, api, learner = maths_api
    for i in range(5):
        pid = client.post("/api/maths/start", json={"learner_id": learner.id, "language": "ne"}).json()["id"]
        assert pid.startswith("ktest-")
        if i == 0:
            api._maths.clear()  # a restart between showing and answering
        r = client.post(f"/api/maths/{pid}/answer", json={"answer": 3}).json()
        assert r["correct"]
    assert r["level_change"] == "up" and learner.maths["ne"]["level"] == 2
    prog = client.get(f"/api/learners/{learner.id}/maths/ne").json()
    assert prog["level"] == 2 and prog["week"]["first_try"] == 1.0
    assert client.post("/api/maths/nobody-123/answer", json={"answer": 1}).status_code == 404


def test_daily_limit_covers_maths(maths_api, monkeypatch):
    client, api, learner = maths_api
    learner.settings["daily_minutes"] = 10
    monkeypatch.setattr(api, "_used_today", lambda l: 10)
    r = client.post("/api/maths/start", json={"learner_id": learner.id, "language": "ne"})
    assert r.status_code == 403 and r.json()["detail"] == "daily_limit"


def test_every_fourth_problem_the_cat_answers_and_the_child_checks(maths_api):
    client, api, learner = maths_api
    probs = [client.post("/api/maths/start", json={"learner_id": learner.id, "language": "ne"}).json() for _ in range(4)]
    assert [p["cat_answer"] is not None for p in probs] == [False, False, False, True]
    p = probs[3]
    cat_right = p["cat_answer"] == 3  # the fixed problem is 2 + 1
    r = client.post(f"/api/maths/{p['id']}/judge", json={"cat_right": cat_right}).json()
    assert r["judged_right"] and r["cat_was_right"] == cat_right
    assert (r["result"] is not None) == cat_right  # agreeing with a right cat solves it
    assert client.post(f"/api/maths/{probs[0]['id']}/judge", json={"cat_right": True}).status_code == 404
    prog = client.get(f"/api/learners/{learner.id}/maths/ne").json()
    assert prog["cat_checks"] == {"judged": 1, "right": 1}


def test_slow_right_answers_are_neutral_for_the_level():
    from athena.maths_progress import first_try_result

    assert first_try_result(True, 12, 1) is True
    assert first_try_result(True, 75, 1) is None  # right, but slow
    assert first_try_result(False, 5, 1) is False
    slow = [True, None, True, None, True]
    assert next_maths_level(1, slow) == 1  # only 3 fluent of 5: not yet
    assert next_maths_level(1, slow + [True, True]) == 2  # last 5: T N T T T = 4 fluent
    assert next_maths_level(2, [None, None, None]) == 2  # slow is not a miss

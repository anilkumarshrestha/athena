"""Mastery update rule (PLAN §5). Offline."""

from athena.mastery import UnitState, allowed, apply_session, practice_targets


def units(**states):
    return {k.replace("_", ":", 1): v for k, v in states.items()}


def test_correct_three_sessions_running_masters():
    u = {"c:क": UnitState("practicing", streak=0, seen=2)}
    for _ in range(2):
        assert apply_session(u, {"c:क": 1}, {}) == []
    changes = apply_session(u, {"c:क": 2}, {})
    assert u["c:क"].state == "mastered"
    assert [(c.unit, c.before, c.after) for c in changes] == [("c:क", "practicing", "mastered")]


def test_never_auto_master_below_three_sightings():
    u = {"c:क": UnitState("practicing", streak=0, seen=0)}
    apply_session(u, {"c:क": 1}, {})
    apply_session(u, {"c:क": 1}, {})
    assert u["c:क"].state == "practicing"  # streak 2, seen 2
    apply_session(u, {"c:क": 1}, {})
    assert u["c:क"].state == "mastered"  # streak 3, seen 3


def test_wrong_twice_in_one_session_demotes_with_cooldown():
    u = {"c:घ": UnitState("mastered", streak=5, seen=9)}
    changes = apply_session(u, {}, {"c:घ": 2})
    assert u["c:घ"].state == "practicing"
    assert u["c:घ"].streak == 0
    assert u["c:घ"].cooldown == 1
    assert [(c.unit, c.after) for c in changes] == [("c:घ", "practicing")]
    assert "c:घ" not in allowed(u)  # next story avoids it


def test_cooldown_ends_after_one_session():
    u = {"c:घ": UnitState("practicing", streak=0, seen=9, cooldown=1), "c:क": UnitState("mastered", 3, 3)}
    apply_session(u, {"c:क": 1}, {})  # a session without घ
    assert u["c:घ"].cooldown == 0
    assert "c:घ" in allowed(u)
    assert practice_targets(u) == ["c:घ"]


def test_single_error_resets_streak_but_does_not_demote():
    u = {"c:क": UnitState("mastered", streak=4, seen=6)}
    assert apply_session(u, {"c:क": 3}, {"c:क": 1}) == []
    assert u["c:क"].state == "mastered" and u["c:क"].streak == 0


def test_unseen_units_never_allowed():
    u = {"c:क": UnitState("mastered", 3, 3), "c:ख": UnitState("unseen")}
    assert allowed(u) == frozenset({"c:क"})


def test_units_not_in_session_untouched():
    u = {"c:क": UnitState("practicing", streak=1, seen=1)}
    apply_session(u, {}, {})
    assert (u["c:क"].streak, u["c:क"].seen) == (1, 1)

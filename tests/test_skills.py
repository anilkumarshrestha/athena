"""Skill graph: prerequisites for reading units and the maths chain."""

from athena.mastery import UnitState
from athena.progression import next_units
from athena.skills import ANY_CONSONANT, maths_skills, missing, prerequisites


def test_reading_prerequisites():
    assert prerequisites("ne", "k:क्त") == ["c:क", "c:त"] and prerequisites("ne", "k:क्ष") == []
    assert prerequisites("ne", "m:ी") == ["m:ि"]
    assert prerequisites("ne", "c:ख") == ["c:क"]
    assert prerequisites("ne", "m:ा") == [ANY_CONSONANT]
    assert prerequisites("ne", "c:क") == []
    assert set(prerequisites("en", "g:sh")) == {"g:s", "g:h"}
    assert missing("ne", "m:ा", {"c:अ"}) == [ANY_CONSONANT] and missing("ne", "m:ा", {"c:क"}) == []


def test_next_units_never_jump_a_prerequisite():
    from athena.progression import STARTER_UNTIL, readable_count

    units = {s: UnitState("mastered", 3, 3) for s in ["c:अ", "c:आ", "c:म", "c:न", "c:र", "c:स", "m:ा", "m:ि"]}
    for _ in range(40):  # walk the progression; past the starter order, prerequisites come first
        nxt = next_units("ne", units, k=1)
        if not nxt:
            break
        known = {s for s, u in units.items() if u.state != "unseen"}
        if readable_count("ne", frozenset(known)) >= STARTER_UNTIL:
            assert not missing("ne", nxt[0], known), nxt[0]
        units[nxt[0]] = UnitState("mastered", 3, 3)


def test_maths_chain_status():
    rec = lambda a, b, op, ok: {"lang": "ne", "a": a, "b": b, "op": op, "answers": [1], "first_try": ok}  # noqa: E731
    skills = {s["id"]: s for s in maths_skills([rec(2, 3, "+", True)] * 5, "ne", level=1)}
    assert skills["add5"]["status"] == "mastered"
    assert skills["add10"]["status"] == "ready"  # its prerequisite is mastered
    assert skills["sub10"]["status"] == "locked"
    assert {s["id"]: s for s in maths_skills([rec(1, 2, "+", False)], "ne", 1)}["add5"]["status"] == "learning"
    assert {s["id"]: s for s in maths_skills([rec(8, 3, "-", True)], "ne", 2)}["sub10"]["problems"] == 1
    assert prerequisites("ne", "k:ज्ञ") == [] and prerequisites("ne", "k:स्त") == ["c:स", "c:त"]

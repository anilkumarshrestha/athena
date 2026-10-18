"""Learner profile insights: skill groups, error patterns, pace. Pure code. Offline."""

from athena.insights import error_patterns, pace, skill_groups
from athena.mastery import UnitState

DAY = 86400.0
NOW = 1_800_000_000.0


def M(*sigs):
    return {s: UnitState("mastered", 3, 3) for s in sigs}


def test_skill_groups_strength_gap_not_started():
    units = M("c:क", "c:ख", "c:ग", "c:घ", "c:ङ", "m:ा") | {"m:ि": UnitState("practicing", 0, 1)}
    g = {x.name: x for x in skill_groups("ne", units)}
    assert g["क-वर्ग"].status == "strong" and g["क-वर्ग"].mastered == 5
    assert g["मात्रा"].status == "learning" and g["मात्रा"].practicing == ["m:ि"]
    assert g["ट-वर्ग"].status == "not_started"


def reading(*pairs):
    """pairs of (expected, heard); heard None = skipped."""
    return {
        "type": "reading",
        "words": [
            {"index": i, "expected": e, "heard": h, "outcome": "omitted" if h is None else ("correct" if e == h else "substituted"), "error_units": []}
            for i, (e, h) in enumerate(pairs)
        ],
    }


def test_aspiration_pattern_needs_two_cases():
    once = error_patterns("ne", [reading(("घर", "गर"))])
    assert once == []
    twice = error_patterns("ne", [reading(("घर", "गर")), reading(("धन", "दन"), ("भात", "बात"))])
    assert twice[0].kind == "aspiration" and twice[0].count == 3
    assert ("घ", "ग") in twice[0].examples


def test_english_digraph_dropped():
    p = error_patterns("en", [reading(("ship", "sip"), ("chin", "cin")), reading(("thin", "tin"))])
    assert p[0].kind == "digraph" and p[0].count == 3


def test_skips_are_counted_separately():
    p = error_patterns("ne", [reading(("घर", None), ("आमा", None))])
    assert p[0].kind == "skipped_words" and p[0].count == 2


def test_pace():
    sessions = [
        {"at": NOW - 13 * DAY, "lang": "ne", "accuracy": 0.7, "wcpm": 10.0, "changes": [["c:क", "practicing", "mastered"]]},
        {"at": NOW - 6 * DAY, "lang": "ne", "accuracy": 0.8, "wcpm": 14.0, "changes": [["c:ख", "practicing", "mastered"]]},
        {"at": NOW - 1 * DAY, "lang": "ne", "accuracy": 0.95, "wcpm": 20.0, "changes": [["c:ग", "practicing", "mastered"], ["c:घ", "unseen", "practicing"]]},
    ]
    p = pace("ne", sessions, now=NOW)
    assert p.sessions_14d == 3 and p.mastered_14d == 3
    assert p.wcpm_first == 10.0 and p.wcpm_last == 20.0 and p.trend == "up"


def test_pace_two_readings_going_down():
    s = [{"at": NOW - 2 * DAY, "lang": "ne", "accuracy": 1, "wcpm": 31.6, "changes": []},
         {"at": NOW - 1 * DAY, "lang": "ne", "accuracy": 1, "wcpm": 20.9, "changes": []}]
    assert pace("ne", s, now=NOW).trend == "down"

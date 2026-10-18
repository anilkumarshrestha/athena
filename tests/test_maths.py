"""Maths problems: code picks numbers and computes the answer; drafts are checked. Offline."""

import random

from athena.lexicon import verifier_for
from athena.maths import DIGITS, LEVELS, Problem, _check, numbers_in, pick, to_ne


def test_devanagari_digits_round_trip():
    assert to_ne(12) == "१२" and numbers_in("सीतासँग ३ केरा, २ थप") == [3, 2]


def test_pick_respects_level_limits():
    rng = random.Random(0)
    for level, (top, ops) in LEVELS.items():
        for _ in range(200):
            a, b, op, _ = pick("ne", level, {"केरा"}, rng)
            assert op in ops
            assert (a + b <= top) if op == "+" else (0 < a - b and a <= top)


def test_answer_is_computed_by_code():
    assert Problem("ne", 3, 2, "+", "केरा").answer == 5
    assert Problem("ne", 7, 4, "-", "केरा").answer == 3


def test_check_rejects_wrong_numbers_and_missing_question():
    p = Problem("ne", 3, 2, "+", "केरा")
    v = verifier_for("ne", frozenset({"c:क", "m:े", "c:र", "m:ा"}), DIGITS)
    assert any("numbers" in x for x in _check(p, ["केरा ३ केरा ४"], v))
    assert any("question" in x for x in _check(p, ["केरा ३ केरा २"], v))
    assert _check(p, ["केरा ३", "केरा २ ?"], v) == []

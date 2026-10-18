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


def test_answers_are_spread_not_always_the_top():
    from collections import Counter

    rng = random.Random(1)
    for level, (top, _) in LEVELS.items():
        answers = Counter()
        for _ in range(2000):
            a, b, op, _n = pick("ne", level, {"केरा"}, rng)
            answers[a + b if op == "+" else a - b] += 1
        assert max(answers.values()) / 2000 < 0.3, (level, answers.most_common(3))


def test_nepali_plural_question_required():
    p = Problem("ne", 1, 3, "+", "किताब")
    v = verifier_for("ne", frozenset({"c:क", "m:ि", "c:त", "m:ा", "c:ब", "c:छ", "c:न", "m:्", "c:अ"}), DIGITS | {"कति", "किताब"})
    assert any("plural" in x for x in _check(p, ["किताब १ किताब ३", "अब कति किताब छ?"], v))
    assert not any("plural" in x for x in _check(p, ["किताब १ किताब ३", "अब कति किताब छन्?"], v))


def test_name_must_be_exact_and_attached():
    from athena.maths import Problem, _name_problems, _ne_templates

    assert _name_problems("सीता", "अब सीतोसँग कति बल छन्?")  # misspelt name
    assert _name_problems("सीता", "सीता का ४ कलम थिए। सीता ले २ कलम दिइन्।")  # detached endings
    assert not _name_problems("सीता", "सीताका ४ कलम थिए। सीताले २ कलम दिइन्। अब कति कलम छन्?")
    # plural possessive: सीताका ३ केरा थिए, never सीताको ३ केरा थिए
    lines = {line for t in _ne_templates(Problem("ne", 3, 2, "+", "केरा"), "सीता", "girl") for line in t}
    assert "सीताका ३ केरा थिए।" in lines and "सीताको ३ केरा थिए।" not in lines

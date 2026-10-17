"""Parent dashboard summary + daily time use. Pure code over the session log. Offline."""

from athena.dashboard import summarize, used_minutes_today

DAY = 86400
NOW = 1_800_000_000.0


def session(days_ago, acc=1.0, changes=(), lang="ne", minutes=4, words=8):
    at = NOW - days_ago * DAY
    return {
        "at": at,
        "started": at - minutes * 60,
        "lang": lang,
        "title": "t",
        "accuracy": acc,
        "wcpm": 20.0,
        "words": words,
        "changes": [list(c) for c in changes],
    }


def test_week_counts_only_last_seven_days():
    log = [session(1), session(3, acc=0.5), session(10)]
    s = summarize(log, now=NOW, days=7)
    assert s.stories == 2
    assert s.words_read == 12  # 8 + 4 (half of 8 at 50%)
    assert s.mean_accuracy == 0.75


def test_learned_and_new_units():
    log = [
        session(1, changes=[("c:क", "practicing", "mastered"), ("m:ु", "unseen", "practicing")]),
        session(2, changes=[("c:ग", "practicing", "mastered")]),
    ]
    s = summarize(log, now=NOW, days=7)
    assert s.mastered == ["c:क", "c:ग"]
    assert s.introduced == ["m:ु"]


def test_struggle_alert_after_two_demotions():
    demote = ("c:घ", "mastered", "practicing")
    once = summarize([session(1, changes=[demote])], now=NOW, days=7)
    twice = summarize([session(1, changes=[demote]), session(12, changes=[demote])], now=NOW, days=7)
    assert once.struggling == []
    assert twice.struggling == ["c:घ"]  # looks back 30 days, not just this week


def test_used_minutes_today_caps_each_session():
    log = [session(0, minutes=4), session(0, minutes=45), session(1, minutes=10)]
    assert used_minutes_today(log, open_started=[NOW - 120], now=NOW) == 4 + 10 + 2  # 45 capped at 10

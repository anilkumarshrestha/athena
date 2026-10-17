"""Parent dashboard + time controls, computed from the learner's session log. Pure code.

A session is logged when a story's reading closes (athena/api.py close_session):
  {"at", "started", "lang", "title", "accuracy", "wcpm", "words", "changes": [[unit, before, after]]}

Struggle alert: a unit demoted (mastered -> practising) at least twice in the last
30 days. One slip is normal; twice means the child needs a different approach.
"""

from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime

DAY = 86400
STRUGGLE_DEMOTIONS = 2
STRUGGLE_WINDOW_DAYS = 30
SESSION_CAP_MIN = 10  # a story left open does not count for more than this


@dataclass
class Summary:
    days: int
    stories: int = 0
    words_read: int = 0  # words read correctly
    mean_accuracy: float | None = None
    mean_wcpm: float | None = None
    mastered: list[str] = field(default_factory=list)  # newly mastered this period
    introduced: list[str] = field(default_factory=list)  # new units started this period
    struggling: list[str] = field(default_factory=list)
    per_day: list[int] = field(default_factory=list)  # stories per day, oldest first


def summarize(log: list[dict], now: float, days: int = 7, lang: str | None = None) -> Summary:
    rows = [s for s in log if lang is None or s["lang"] == lang]
    week = [s for s in rows if now - s["at"] <= days * DAY]
    out = Summary(days=days, stories=len(week))
    if week:
        out.words_read = round(sum(s["words"] * s["accuracy"] for s in week))
        out.mean_accuracy = round(sum(s["accuracy"] for s in week) / len(week), 2)
        out.mean_wcpm = round(sum(s["wcpm"] for s in week) / len(week), 1)
    for s in week:
        for unit, before, after in s["changes"]:
            if after == "mastered" and unit not in out.mastered:
                out.mastered.append(unit)
            if before == "unseen" and unit not in out.introduced:
                out.introduced.append(unit)
    demotions = Counter(
        unit
        for s in rows
        if now - s["at"] <= STRUGGLE_WINDOW_DAYS * DAY
        for unit, before, after in s["changes"]
        if before == "mastered" and after == "practicing"
    )
    out.struggling = sorted(u for u, n in demotions.items() if n >= STRUGGLE_DEMOTIONS)
    out.per_day = [sum(1 for s in week if days - 1 - d == int((now - s["at"]) // DAY)) for d in range(days)]
    return out


def _same_day(a: float, b: float) -> bool:
    return datetime.fromtimestamp(a).date() == datetime.fromtimestamp(b).date()


def used_minutes_today(log: list[dict], open_started: list[float], now: float) -> int:
    """Reading minutes today: closed sessions + stories still open, each capped."""
    cap = SESSION_CAP_MIN * 60
    secs = sum(min(s["at"] - s["started"], cap) for s in log if _same_day(s["at"], now))
    secs += sum(min(now - t, cap) for t in open_started if _same_day(t, now))
    return round(secs / 60)

"""Maths progress for parents and teachers. Pure code over stored events.

  {"type": "maths",        "story_id": pid, "at", "lang", "sentences", "a", "b", "op", "source"}
  {"type": "maths_answer", "story_id": pid, "at", "answer", "correct", "try"}

Every number here is computed from what the child tapped; the server decided "correct".
Mistake kinds are named only when the arithmetic shows them:
  off_by_one      answer one away from the right one (a counting slip)
  wrong_operation added when the problem took away, or took away when it added

Maths has its own level per language (athena.maths.LEVELS: 1 = adding to 5, 2 = +/- to 10,
3 = +/- to 20), separate from reading: a strong reader can still be new to sums.
"""

DAY = 86400.0
MIN_FOR_STRUGGLE = 3  # problems of one kind before we call it hard
STRUGGLE_BELOW = 0.5  # first-try rate
UP_WINDOW, UP_NEEDED = 5, 4  # 4 of the last 5 right on the first try -> harder sums
DOWN_RUN = 3  # 3 in a row not right on the first try -> easier sums
MAX_LEVEL = 3
PROBLEM_CAP_S = 180  # a problem left open counts for at most this toward daily time


def next_maths_level(level: int, recent: list[bool]) -> int:
    """recent: first-try results at the current level, oldest first. Reset on a change."""
    if len(recent) >= DOWN_RUN and not any(recent[-DOWN_RUN:]):
        return max(1, level - 1)
    if len(recent) >= UP_WINDOW and sum(recent[-UP_WINDOW:]) >= UP_NEEDED:
        return min(MAX_LEVEL, level + 1)
    return level


def maths_seconds_today(records: list[dict], now: float, same_day) -> float:
    """Time on maths today: from showing each problem to its last tap, capped. The newest
    problem, if not answered yet, counts until now (also capped)."""
    secs = 0.0
    for i, r in enumerate(records):  # newest first
        if not same_day(r["at"], now):
            continue
        end = r["last_at"] if r["answers"] else (now if i == 0 else r["at"])
        secs += min(max(0.0, end - r["at"]), PROBLEM_CAP_S)
    return secs


def fold_maths(events: list[dict]) -> list[dict]:
    """Events (in write order) -> one record per problem, newest first."""
    records: dict[str, dict] = {}
    for e in events:
        pid = e.get("story_id")
        if e.get("type") == "maths":
            a, b, op = e["a"], e["b"], e["op"]
            records[pid] = {
                "id": pid, "at": e["at"], "lang": e["lang"], "sentences": e.get("sentences", []),
                "a": a, "b": b, "op": op, "answer": a + b if op == "+" else a - b,
                "source": e.get("source", ""), "level": e.get("level"), "answers": [], "solved": False,
                "last_at": e["at"],
            }
        elif e.get("type") == "maths_answer" and pid in records:
            r = records[pid]
            r["answers"].append(e["answer"])
            r["last_at"] = e.get("at", r["last_at"])
            r["solved"] = r["solved"] or bool(e.get("correct"))
    for r in records.values():
        r["first_try"] = bool(r["answers"]) and r["answers"][0] == r["answer"]
        r["mistakes"] = [k for x in r["answers"] if x != r["answer"] for k in [mistake_kind(r, x)] if k]
    return sorted(records.values(), key=lambda r: r["at"], reverse=True)


def mistake_kind(r: dict, given: int) -> str | None:
    other = r["a"] - r["b"] if r["op"] == "+" else r["a"] + r["b"]
    if given == other and other != r["answer"]:
        return "wrong_operation"
    if abs(given - r["answer"]) == 1:
        return "off_by_one"
    return None


def _rate(rs: list[dict]) -> float | None:
    tried = [r for r in rs if r["answers"]]
    return round(sum(r["first_try"] for r in tried) / len(tried), 2) if tried else None


def summarize_maths(records: list[dict], lang: str, now: float, level: int = 1, days: int = 7, recent: int = 10) -> dict:
    rs = [r for r in records if r["lang"] == lang]
    week = [r for r in rs if r["at"] >= now - days * DAY]
    per_day = [0] * days
    for r in week:
        i = days - 1 - int((now - r["at"]) // DAY)
        if 0 <= i < days:
            per_day[i] += 1
    by_op = {}
    for op in ("+", "-"):
        mine = [r for r in rs if r["op"] == op and r["answers"]]
        by_op[op] = {"problems": len(mine), "first_try": _rate(mine)}
    struggling = [op for op, s in by_op.items()
                  if s["problems"] >= MIN_FOR_STRUGGLE and (s["first_try"] or 0) < STRUGGLE_BELOW]
    mistakes: dict[str, int] = {}
    for r in rs:
        for k in r["mistakes"]:
            mistakes[k] = mistakes.get(k, 0) + 1
    return {
        "lang": lang,
        "level": level,
        "total": len(rs),
        "week": {
            "problems": len(week),
            "answered": sum(1 for r in week if r["answers"]),
            "solved": sum(1 for r in week if r["solved"]),
            "first_try": _rate(week),
            "per_day": per_day,
        },
        "all_first_try": _rate(rs),
        "by_op": by_op,
        "struggling": struggling,
        "mistakes": mistakes,
        "largest_solved": max((r["answer"] for r in rs if r["first_try"]), default=None),
        "recent": [
            {k: r[k] for k in ("id", "at", "sentences", "a", "b", "op", "answer", "answers", "solved", "first_try")}
            for r in rs[:recent]
        ],
    }

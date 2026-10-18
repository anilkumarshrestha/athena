"""Which way of re-teaching works for this child. Pure code over stored events.

The re-teach card shows one way at a time (hear it, see its parts, see a picture) and offers
"another way". Each retry is logged:

  {"type": "reteach", "story_id", "at", "index", "word", "styles": ["hear", "parts"], "correct": true,
   "trigger": "tap" | "repeat" | "pause"}   (repeat/pause: the card opened itself, see auto_target)

"styles" are the ways the child used before this retry, in order. The LAST one gets the
credit (or the blame): it is what the child saw just before reading the word again.
The card then opens with the way that has worked best for this child.
"""

STYLES = ("hear", "parts", "picture")
DEFAULT_ORDER = STYLES  # hearing first: the most direct help for a beginner
MIN_EVIDENCE = 2  # tries before a style's own record outweighs the default order


def style_stats(events: list[dict]) -> dict[str, dict[str, int]]:
    """Per style: retries it led into, and how many of those were read right."""
    out = {s: {"tries": 0, "worked": 0} for s in STYLES}
    for e in events:
        styles = [s for s in e.get("styles", []) if s in out]
        if not styles:
            continue
        last = styles[-1]
        out[last]["tries"] += 1
        out[last]["worked"] += bool(e.get("correct"))
    return out


def style_order(events: list[dict], has_picture: bool) -> list[str]:
    """Best first. Laplace-smoothed success rate; styles with little evidence keep their default place."""
    stats = style_stats(events)

    def score(s: str) -> tuple[float, int]:
        st = stats[s]
        rate = (st["worked"] + 1) / (st["tries"] + 2) if st["tries"] >= MIN_EVIDENCE else 0.5
        return (-rate, DEFAULT_ORDER.index(s))

    return sorted((s for s in STYLES if has_picture or s != "picture"), key=score)


def best_style(events: list[dict]) -> dict | None:
    """For parents: the way that helps most, once there is enough evidence."""
    stats = style_stats(events)
    known = [(s, st) for s, st in stats.items() if st["tries"] >= MIN_EVIDENCE]
    if not known:
        return None
    s, st = max(known, key=lambda x: (x[1]["worked"] / x[1]["tries"], x[1]["tries"]))
    return {"style": s, "worked": st["worked"], "tries": st["tries"]}


# --- automatic re-teach: when to open the card without a tap ------------------------------

WRONG = ("substituted", "omitted")
PAUSE_S = 4  # the live guide stayed on one word this long (measured in the browser)


def auto_target(words: list[dict], paused: set[int]) -> dict | None:
    """After a reading, the one word worth re-teaching right away, or None.

    1. "repeat": the same letter/sign was behind mistakes in two or more words. The first
       such word is re-taught: one confusion explains several misses.
    2. "pause":  the child stopped on a word for PAUSE_S or more and then misread it.
    A long pause on a word read right is not interrupted: the child worked it out.
    """
    wrong = [w for w in words if w["outcome"] in WRONG]
    seen: dict[str, int] = {}
    for w in wrong:
        for u in w.get("error_units", []):
            seen[u] = seen.get(u, 0) + 1
    for w in wrong:
        if any(seen.get(u, 0) >= 2 for u in w.get("error_units", [])):
            return {"index": w["index"], "reason": "repeat"}
    for w in wrong:
        if w["index"] in paused:
            return {"index": w["index"], "reason": "pause"}
    return None

"""Which way of re-teaching works for this child. Pure code over stored events.

The re-teach card shows one way at a time (hear it, see its parts, see a picture) and offers
"another way". Each retry is logged:

  {"type": "reteach", "story_id", "at", "index", "word", "styles": ["hear", "parts"], "correct": true}

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

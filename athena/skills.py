"""Skill graph: what each unit needs first, for reading and maths. Pure code.

Reading (units are verifier signatures):
  Nepali  conjunct k:क्ष      needs both its letters (c:क, c:ष)
          long vowel sign     needs its short one (ी after ि, ू after ु, ै after े, ौ after ो)
          breathy letter      needs its plain partner (ख after क, घ after ग, ...)
          any vowel sign      needs a consonant to sit on (at least one known)
  English multi-letter sound  needs its letters, when they are taught on their own (sh: s, h)
Choosing the next units (athena.progression.next_units) respects this graph after the
hand-picked starter order (the first ~30 words: छ "is" comes early, before च); the teacher
view shows it, so "why not त्र yet?" has an answer: "it needs र first".

Maths: adding to 5 -> adding to 10 -> taking away within 10 -> adding / taking away to 20.
"""

from athena.insights import ASPIRATION

LONG_AFTER_SHORT = {"m:ी": "m:ि", "m:ू": "m:ु", "m:ै": "m:े", "m:ौ": "m:ो"}
PLAIN_FOR = {f"c:{breathy}": f"c:{plain}" for plain, breathy in ASPIRATION}
ANY_CONSONANT = "any consonant"  # pseudo-prerequisite for vowel signs
VARNAMALA_CONJUNCTS = frozenset({"क्ष", "त्र", "ज्ञ"})  # end of the alphabet chart: learned whole
NE_VOWELS = frozenset("अ आ इ ई उ ऊ ऋ ए ऐ ओ औ".split())  # also "c:" signatures, but not consonants


def prerequisites(language: str, unit: str) -> list[str]:
    from athena.progression import SEQUENCE

    kind, _, glyph = unit.partition(":")
    if language == "ne":
        if kind == "k":
            if glyph in VARNAMALA_CONJUNCTS:
                return []  # taught as letters of the alphabet, not built from their parts
            return [f"c:{c}" for c in glyph.replace("्", "")]
        if kind == "m":
            return [LONG_AFTER_SHORT[unit]] if unit in LONG_AFTER_SHORT else [ANY_CONSONANT]
        if unit in PLAIN_FOR:
            return [PLAIN_FOR[unit]]
        return []
    if kind == "g" and len(glyph.replace("_", "")) > 1:
        singles = set(SEQUENCE["en"])
        letters = dict.fromkeys(glyph.replace("_", ""))
        return [f"g:{c}" for c in letters if f"g:{c}" in singles and f"g:{c}" != unit]
    return []


def missing(language: str, unit: str, known: frozenset[str] | set[str]) -> list[str]:
    """Prerequisites of unit not yet known (mastered or practising)."""
    out = []
    for p in prerequisites(language, unit):
        if p == ANY_CONSONANT:
            if not any(k.startswith("c:") and k[2:] not in NE_VOWELS for k in known):
                out.append(p)
        elif p not in known:
            out.append(p)
    return out


def waiting(language: str, units: dict, limit: int = 12) -> list[dict]:
    """Unseen units held back by a prerequisite, in teaching order: [{unit, needs: [{unit, known}]}]."""
    from athena.progression import SEQUENCE

    known = {s for s, u in units.items() if u.state in ("mastered", "practicing")}
    out = []
    for s in SEQUENCE[language]:
        if s in known:
            continue
        if miss := missing(language, s, known):
            out.append({"unit": s, "needs": [{"unit": p, "known": p not in miss} for p in prerequisites(language, s)]})
        if len(out) == limit:
            break
    return out


# --- maths --------------------------------------------------------------------------------

MATHS_SKILLS = [  # (id, level, op, label_en, label_ne, prerequisite)
    ("add5", 1, "+", "Adding to 5", "५ सम्म जोड", None),
    ("add10", 2, "+", "Adding to 10", "१० सम्म जोड", "add5"),
    ("sub10", 2, "-", "Taking away within 10", "१० भित्र घटाउ", "add10"),
    ("add20", 3, "+", "Adding to 20", "२० सम्म जोड", "add10"),
    ("sub20", 3, "-", "Taking away within 20", "२० भित्र घटाउ", "sub10"),
]
SKILL_MASTERED = (5, 0.8)  # at least 5 answered, 80% right on the first try


def skill_level(r: dict) -> int:
    """Which band a problem belongs to, from its numbers (works for old logs without a level)."""
    top = max(r["a"], r["a"] + r["b"] if r["op"] == "+" else r["a"])
    return 1 if top <= 5 and r["op"] == "+" else 2 if top <= 10 else 3


def maths_skills(records: list[dict], lang: str, level: int) -> list[dict]:
    """Each maths skill with its status: mastered / learning / ready / locked (icon + word in the UI)."""
    out: dict[str, dict] = {}
    for sid, lvl, op, en, ne, pre in MATHS_SKILLS:
        mine = [r for r in records if r["lang"] == lang and skill_level(r) == lvl and r["op"] == op and r["answers"]]
        rate = round(sum(r["first_try"] for r in mine) / len(mine), 2) if mine else None
        if len(mine) >= SKILL_MASTERED[0] and (rate or 0) >= SKILL_MASTERED[1]:
            status = "mastered"
        elif mine:
            status = "learning"
        elif lvl <= level or (pre and out[pre]["status"] == "mastered"):
            status = "ready"
        else:
            status = "locked"
        out[sid] = {"id": sid, "label_en": en, "label_ne": ne, "needs": pre, "problems": len(mine),
                    "first_try": rate, "status": status}
    return list(out.values())

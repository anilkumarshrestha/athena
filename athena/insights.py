"""Learner profile insights for parents and teachers. Pure code over stored data.

  skill_groups   strengths and gaps by the groups children are taught in (varnamala rows,
                 phonics sets), from unit states
  error_patterns what kind of mistakes the child makes, from per-word reading history:
                 aspiration (घ->ग), retroflex/dental (ट->त), vowel sign swaps, English
                 digraphs dropped (sh->s), b/d, short vowels; skipped words
  pace           sessions and units mastered in 14 days, words-per-minute trend

Every number is computed here; a model may only phrase them (athena/agents/coach.py).
"""

from dataclasses import dataclass, field

from athena.lexicon import en_lexicon
from athena.mastery import UnitState
from athena.verifier.english import SPLIT_MARKER
from athena.verifier.nepali import DecomposeError, decompose

DAY = 86400.0

# --- skill groups ----------------------------------------------------------------------

NE_GROUPS: list[tuple[str, str]] = [
    ("स्वर", "c:अ c:आ c:इ c:ई c:उ c:ऊ c:ऋ c:ए c:ऐ c:ओ c:औ"),
    ("क-वर्ग", "c:क c:ख c:ग c:घ c:ङ"),
    ("च-वर्ग", "c:च c:छ c:ज c:झ c:ञ"),
    ("ट-वर्ग", "c:ट c:ठ c:ड c:ढ c:ण"),
    ("त-वर्ग", "c:त c:थ c:द c:ध c:न"),
    ("प-वर्ग", "c:प c:फ c:ब c:भ c:म"),
    ("अन्तस्थ", "c:य c:र c:ल c:व"),
    ("ऊष्म", "c:श c:ष c:स c:ह"),
    ("मात्रा", "m:ा m:ि m:ी m:ु m:ू m:ृ m:े m:ै m:ो m:ौ m:ं m:ँ m:ः"),
]
EN_GROUPS: list[tuple[str, str]] = [
    ("Set 1", "g:s g:a g:t g:p g:i g:n"),
    ("Set 2", "g:m g:d g:g g:o g:c g:k"),
    ("Set 3", "g:ck g:e g:u g:r g:h g:b g:f g:l"),
    ("Set 4", "g:ff g:ll g:ss g:j g:v g:w g:x g:y g:z g:qu"),
    ("Digraphs", "g:sh g:ch g:th g:ng"),
    ("Vowel teams", "g:ai g:ee g:igh g:oa g:oo g:ar g:or g:ur g:ow g:oi g:ear"),
]


@dataclass
class Group:
    name: str
    total: int
    mastered: int
    practicing: list[str]
    status: str  # strong | learning | not_started


def skill_groups(language: str, units: dict[str, UnitState]) -> list[Group]:
    groups = [(n, u.split()) for n, u in (NE_GROUPS if language == "ne" else EN_GROUPS)]
    conj = sorted(s for s in units if s.startswith("k:"))
    if language == "ne" and conj:
        groups.append(("संयुक्त", conj))
    out = []
    for name, sigs in groups:
        st = [units.get(s) for s in sigs]
        mastered = sum(1 for u in st if u and u.state == "mastered")
        practicing = [s for s, u in zip(sigs, st) if u and u.state == "practicing"]
        if mastered / len(sigs) >= 0.8:
            status = "strong"
        elif mastered or practicing:
            status = "learning"
        else:
            status = "not_started"
        out.append(Group(name, len(sigs), mastered, practicing, status))
    return out


# --- error patterns ----------------------------------------------------------------------

ASPIRATION = [("क", "ख"), ("ग", "घ"), ("च", "छ"), ("ज", "झ"), ("ट", "ठ"), ("ड", "ढ"), ("त", "थ"), ("द", "ध"), ("प", "फ"), ("ब", "भ")]
RETROFLEX = [("ट", "त"), ("ठ", "थ"), ("ड", "द"), ("ढ", "ध"), ("ण", "न")]
_PAIRS = {frozenset(p): kind for kinds, kind in ((ASPIRATION, "aspiration"), (RETROFLEX, "retroflex_dental")) for p in kinds}
EN_DIGRAPHS = {"sh", "ch", "th", "ng", "ck", "qu"}
EN_SHORT_VOWELS = set("aeiou")

LABEL = {
    "aspiration": ("breathy letters (घ↔ग, ध↔द, भ↔ब)", "महाप्राण अक्षर (घ↔ग, ध↔द, भ↔ब)"),
    "retroflex_dental": ("ट-row vs त-row letters (ट↔त, ड↔द)", "ट-वर्ग र त-वर्ग (ट↔त, ड↔द)"),
    "vowel_sign": ("vowel signs (कि↔का, को↔कु)", "मात्रा (कि↔का, को↔कु)"),
    "other_letter": ("other letter swaps", "अरू अक्षर"),
    "digraph": ("two-letter sounds dropped (sh→s, ch→c, th→t)", "दुई अक्षरको आवाज (sh, ch, th)"),
    "b_d": ("b and d mixed up", "b र d"),
    "short_vowel": ("short vowel sounds (a, e, i, o, u)", "छोटा स्वर (a, e, i, o, u)"),
    "skipped_words": ("skipping words", "शब्द छुटाउने"),
}
MIN_COUNT = 2


@dataclass
class Pattern:
    kind: str
    count: int
    examples: list[tuple[str, str]] = field(default_factory=list)
    label_en: str = ""
    label_ne: str = ""


def _ne_kinds(expected: str, heard: str) -> list[tuple[str, tuple[str, str]]]:
    try:
        e, h = decompose(expected), decompose(heard)
    except DecomposeError:
        return []
    if len(e) != len(h):
        return []
    out = []
    for a, b in zip(e, h):
        if a.base != b.base:
            out.append((_PAIRS.get(frozenset((a.base, b.base)), "other_letter"), (a.base, b.base)))
        elif (a.matra or "") != (b.matra or ""):
            out.append(("vowel_sign", (a.text, b.text)))
    return out


def _en_kinds(expected: str, heard: str) -> list[tuple[str, tuple[str, str]]]:
    lex = en_lexicon()
    e = lex.get(expected.lower())
    eg = [g for g in (e.graphemes or ()) if g != SPLIT_MARKER] if e else []
    out = []
    for g in eg:
        if g in EN_DIGRAPHS and g not in heard and g[0] in heard:
            out.append(("digraph", (g, g[0])))
    if {expected[:1], heard[:1]} == {"b", "d"}:
        out.append(("b_d", (expected[:1], heard[:1])))
    if len(expected) == len(heard) == 3 and expected[0] == heard[0] and expected[2] == heard[2]:
        if expected[1] in EN_SHORT_VOWELS and heard[1] in EN_SHORT_VOWELS and expected[1] != heard[1]:
            out.append(("short_vowel", (expected[1], heard[1])))
    return out


def error_patterns(language: str, readings: list[dict]) -> list[Pattern]:
    found: dict[str, Pattern] = {}
    for r in readings:
        for w in r.get("words", []):
            if w["outcome"] == "omitted":
                kinds = [("skipped_words", (w["expected"], "—"))]
            elif w["outcome"] == "substituted" and w.get("heard"):
                kinds = (_ne_kinds if language == "ne" else _en_kinds)(w["expected"], w["heard"])
            else:
                continue
            for kind, ex in kinds:
                p = found.setdefault(kind, Pattern(kind, 0, [], *LABEL[kind]))
                p.count += 1
                if ex not in p.examples and len(p.examples) < 4:
                    p.examples.append(ex)
    return sorted((p for p in found.values() if p.count >= MIN_COUNT), key=lambda p: -p.count)


# --- pace -------------------------------------------------------------------------------


@dataclass
class Pace:
    sessions_14d: int
    mastered_14d: int
    wcpm_first: float | None
    wcpm_last: float | None
    trend: str  # up | flat | down | unknown


def pace(language: str, sessions: list[dict], now: float) -> Pace:
    recent = sorted((s for s in sessions if s["lang"] == language and now - s["at"] <= 14 * DAY), key=lambda s: s["at"])
    mastered = sum(1 for s in recent for u, _b, a in s.get("changes", []) if a == "mastered")
    reads = [s["wcpm"] for s in recent if s.get("wcpm")]
    k = 2 if len(reads) >= 4 else 1  # average pairs only when they don't overlap
    first = sum(reads[:k]) / k if reads else None
    last = sum(reads[-k:]) / k if reads else None
    if len(reads) < 2:
        trend = "unknown"
    elif last > first * 1.1:
        trend = "up"
    elif last < first * 0.9:
        trend = "down"
    else:
        trend = "flat"
    return Pace(len(recent), mastered, reads[0] if reads else None, reads[-1] if reads else None, trend)

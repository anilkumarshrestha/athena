"""Reading assessment against a known reference text. Pure stdlib + verifier code.

We always know what the child should read, so this is alignment, not open
transcription. Each reference word gets one outcome:

  correct | substituted | omitted | self_corrected
plus a list of inserted words.

We can only score what can be HEARD. Nepali spelling distinguishes things speech
does not: vowel length (इ/ई, उ/ऊ, ि/ी, ु/ू), श/ष/स, and in everyday speech व/ब.
Words are compared on a pronunciation fold, so दूध read as "दुध" is correct (they
sound the same). Nasal marks (ँ ं) are not scored at all: speech-to-text drops them
on correct reads (probe 17 Oct), so scoring them would punish children for STT errors.

Word alignment is weighted Levenshtein on folded words: similar words cost less to
substitute, so "गरमा" lines up with "घरमा" instead of one insertion plus one omission.

Error units: the expected word's units whose sound the heard word lacks (घरमा→गरमा
blames c:घ). If that diff is empty, or the heard word cannot be decomposed, every
scored unit of the expected word is blamed. Omitted words blame all scored units.
"""

import difflib
from collections import Counter
from dataclasses import dataclass, field
from typing import Literal

from athena.lexicon import en_lexicon
from athena.verifier.english import grapheme_signatures
from athena.verifier.english import tokenize as en_tokenize
from athena.verifier.nepali import DecomposeError, decompose
from athena.verifier.nepali import tokenize as ne_tokenize

Outcome = Literal["correct", "substituted", "omitted", "self_corrected"]

SELF_CORRECT_SIM = 0.5  # an inserted near-miss right before the correct word

# Spelling distinctions with no reliable audible difference in spoken Nepali.
_NE_FOLD = str.maketrans({"ी": "ि", "ू": "ु", "ई": "इ", "ऊ": "उ", "श": "स", "ष": "स", "व": "ब", "ँ": None, "ं": None})
_NE_UNSCORED = {"m:ँ", "m:ं"}


@dataclass(frozen=True)
class WordResult:
    index: int
    expected: str
    heard: str | None
    outcome: Outcome
    error_units: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class Insertion:
    word: str
    before_index: int  # reference index it precedes (len(ref) = at the end)


@dataclass(frozen=True)
class Assessment:
    words: list[WordResult]
    insertions: list[Insertion]
    words_correct: int
    wcpm: float
    unit_errors: dict[str, int]
    unit_correct: dict[str, int]


def tokens(lang: str, text: str) -> list[str]:
    return ne_tokenize(text) if lang == "ne" else en_tokenize(text)


def fold(lang: str, word: str) -> str:
    """What the word sounds like, as far as reading-aloud scoring can tell."""
    return word.translate(_NE_FOLD) if lang == "ne" else word


def _fold_unit(lang: str, sig: str) -> str | None:
    """Sound of a unit; None if the unit is not scored from audio."""
    if lang != "ne":
        return sig
    if sig in _NE_UNSCORED:
        return None
    kind, glyph = sig.split(":", 1)
    return f"{kind}:{glyph.translate(_NE_FOLD)}"


def units_of(lang: str, word: str) -> list[str] | None:
    """Mastery signatures for a word, or None if it cannot be analysed."""
    if lang == "ne":
        try:
            sigs: list[str] = []
            for u in decompose(word):
                sigs.extend(s for s in sorted(u.signatures()) if s not in sigs)
            return sigs
        except DecomposeError:
            return None
    entry = en_lexicon().get(word)
    if entry is None:
        return None
    return grapheme_signatures(entry.graphemes) if entry.graphemes else ["w:" + word]


def _scored(lang: str, sigs: list[str]) -> list[str]:
    return [s for s in sigs if _fold_unit(lang, s) is not None]


def _sim(a: str, b: str) -> float:
    return difflib.SequenceMatcher(a=a, b=b, autojunk=False).ratio()


def _sub_cost(a: str, b: str) -> float:
    return 0.0 if a == b else 0.5 + 0.5 * (1 - _sim(a, b))


def _align(ref: list[str], hyp: list[str]) -> list[tuple[int | None, int | None]]:
    """Weighted Levenshtein; returns (ref_i, hyp_j) pairs, None marks a gap."""
    n, m = len(ref), len(hyp)
    cost = [[0.0] * (m + 1) for _ in range(n + 1)]
    for i in range(1, n + 1):
        cost[i][0] = float(i)
    for j in range(1, m + 1):
        cost[0][j] = float(j)
    for i in range(1, n + 1):
        for j in range(1, m + 1):
            cost[i][j] = min(
                cost[i - 1][j - 1] + _sub_cost(ref[i - 1], hyp[j - 1]), cost[i - 1][j] + 1, cost[i][j - 1] + 1
            )

    pairs: list[tuple[int | None, int | None]] = []
    i, j = n, m
    while i > 0 or j > 0:
        if i > 0 and j > 0 and cost[i][j] == cost[i - 1][j - 1] + _sub_cost(ref[i - 1], hyp[j - 1]):
            pairs.append((i - 1, j - 1))
            i, j = i - 1, j - 1
        elif i > 0 and cost[i][j] == cost[i - 1][j] + 1:
            pairs.append((i - 1, None))
            i -= 1
        else:
            pairs.append((None, j - 1))
            j -= 1
    return pairs[::-1]


def _error_units(lang: str, expected: str, heard: str | None) -> list[str]:
    exp = _scored(lang, units_of(lang, expected) or [])
    if heard is None:
        return exp
    got = units_of(lang, heard)
    if got is None:
        return exp
    got_sounds = {_fold_unit(lang, u) for u in got}
    diff = [u for u in exp if _fold_unit(lang, u) not in got_sounds]
    return diff or exp


def assess(
    lang: str,
    reference: str,
    hypothesis: str,
    duration_s: float,
    allowed_words: frozenset[str] = frozenset(),
) -> Assessment:
    ref, hyp = tokens(lang, reference), tokens(lang, hypothesis)
    ref_f, hyp_f = [fold(lang, w) for w in ref], [fold(lang, w) for w in hyp]
    pairs = _align(ref_f, hyp_f)

    results: dict[int, WordResult] = {}
    insertions: list[Insertion] = []
    pending: list[int] = []  # hyp indices of insertions waiting to see what follows

    def flush(before: int) -> None:
        insertions.extend(Insertion(hyp[j], before) for j in pending)
        pending.clear()

    for k, (ri, hj) in enumerate(pairs):
        if ri is None:
            # STT sometimes splits one word in two ("हास्नु हुन्छ"): glue it back.
            prev = pairs[k - 1] if k else (None, None)
            pr = prev[0]
            if pr is not None and results.get(pr) and results[pr].outcome == "substituted" and prev[1] is not None:
                if hyp_f[prev[1]] + hyp_f[hj] == ref_f[pr]:
                    results[pr] = WordResult(pr, ref[pr], ref[pr], "correct")
                    continue
            pending.append(hj)
            continue
        expected = ref[ri]
        if hj is not None and hyp_f[hj] == ref_f[ri]:
            # Inserted words right before a correct word: a repetition is not an
            # error; a near-miss is a self-correction.
            near = [j for j in pending if hyp_f[j] != ref_f[ri] and _sim(hyp_f[j], ref_f[ri]) >= SELF_CORRECT_SIM]
            pending[:] = [j for j in pending if hyp_f[j] != ref_f[ri] and j not in near]
            flush(ri)
            outcome: Outcome = "self_corrected" if near else "correct"
            results[ri] = WordResult(ri, expected, hyp[hj], outcome)
        else:
            flush(ri)
            heard = hyp[hj] if hj is not None else None
            outcome = "substituted" if heard is not None else "omitted"
            units = [] if expected in allowed_words else _error_units(lang, expected, heard)
            results[ri] = WordResult(ri, expected, heard, outcome, units)
    flush(len(ref))

    words = [results[i] for i in range(len(ref))]
    correct = sum(w.outcome in ("correct", "self_corrected") for w in words)

    unit_errors: Counter[str] = Counter()
    unit_correct: Counter[str] = Counter()
    for w in words:
        if w.expected in allowed_words:
            continue
        if w.outcome in ("correct", "self_corrected"):
            unit_correct.update(_scored(lang, units_of(lang, w.expected) or []))
        else:
            unit_errors.update(w.error_units)

    return Assessment(
        words=words,
        insertions=insertions,
        words_correct=correct,
        wcpm=round(correct / (duration_s / 60), 1) if duration_s > 0 else 0.0,
        unit_errors=dict(unit_errors),
        unit_correct=dict(unit_correct),
    )

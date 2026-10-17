"""Reading assessment against a known reference text. Pure stdlib + verifier code.

We always know what the child should read, so this is alignment, not open
transcription. Each reference word gets one outcome:

  correct | substituted | omitted | self_corrected
plus a list of inserted words.

Word alignment is weighted Levenshtein where a substitution between similar words
costs less than an unrelated one, so "दुध" lines up with "दूध" instead of being
counted as one insertion plus one omission.

Error units: for a substitution, the expected word's units that the heard word
lacks (दूध→दुध blames m:ू). If that diff is empty, or the heard word cannot be
decomposed, every unit of the expected word is blamed. Omitted words blame all
their units. Explainable on purpose: a teacher must see why.
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


def _sim(a: str, b: str) -> float:
    return difflib.SequenceMatcher(a=a, b=b, autojunk=False).ratio()


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
            sub = 0.0 if ref[i - 1] == hyp[j - 1] else 0.5 + 0.5 * (1 - _sim(ref[i - 1], hyp[j - 1]))
            cost[i][j] = min(cost[i - 1][j - 1] + sub, cost[i - 1][j] + 1, cost[i][j - 1] + 1)

    pairs: list[tuple[int | None, int | None]] = []
    i, j = n, m
    while i > 0 or j > 0:
        if i > 0 and j > 0:
            sub = 0.0 if ref[i - 1] == hyp[j - 1] else 0.5 + 0.5 * (1 - _sim(ref[i - 1], hyp[j - 1]))
            if cost[i][j] == cost[i - 1][j - 1] + sub:
                pairs.append((i - 1, j - 1))
                i, j = i - 1, j - 1
                continue
        if i > 0 and cost[i][j] == cost[i - 1][j] + 1:
            pairs.append((i - 1, None))
            i -= 1
        else:
            pairs.append((None, j - 1))
            j -= 1
    return pairs[::-1]


def _error_units(lang: str, expected: str, heard: str | None) -> list[str]:
    exp = units_of(lang, expected) or []
    if heard is None:
        return exp
    got = units_of(lang, heard)
    if got is None:
        return exp
    diff = [u for u in exp if u not in got]
    return diff or exp


def assess(
    lang: str,
    reference: str,
    hypothesis: str,
    duration_s: float,
    allowed_words: frozenset[str] = frozenset(),
) -> Assessment:
    ref, hyp = tokens(lang, reference), tokens(lang, hypothesis)
    pairs = _align(ref, hyp)

    results: dict[int, WordResult] = {}
    insertions: list[Insertion] = []
    pending: list[str] = []  # insertions waiting to see what follows

    def flush(before: int) -> None:
        insertions.extend(Insertion(w, before) for w in pending)
        pending.clear()

    for ri, hj in pairs:
        if ri is None:
            pending.append(hyp[hj])
            continue
        expected = ref[ri]
        if hj is not None and hyp[hj] == expected:
            # Inserted words right before a correct word: a repetition is not an
            # error; a near-miss is a self-correction.
            near = [w for w in pending if w != expected and _sim(w, expected) >= SELF_CORRECT_SIM]
            pending[:] = [w for w in pending if w != expected and w not in near]
            flush(ri)
            outcome: Outcome = "self_corrected" if near else "correct"
            results[ri] = WordResult(ri, expected, expected, outcome)
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
            unit_correct.update(units_of(lang, w.expected) or [])
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

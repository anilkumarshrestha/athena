"""Teach the cat: the child corrects the tutor (a child-sized Feynman / protégé effect).

The cat reads a story the child has already read, with a few words changed. The child taps
the words the cat got wrong. Code decides everything:
  - which words change: preferring the confusions this child actually makes (from their
    reading history: athena/insights.py error patterns), then letters being practised
  - how they change: only differences you can HEAR. Nepali: breathy vs plain (घ→ग),
    ट-row vs त-row (ट→त), adding or dropping ा. Never vowel length or श/ष/स: reading-aloud
    scoring treats those as sounding the same (athena/assess/align.py), so the cat must too.
    English: b↔d, a short vowel in a 3-letter word (cat→cot), a digraph dropped (ship→sip).
Catching the cat's घ→ग is evidence the child hears the difference.
"""

import random

from athena.insights import ASPIRATION, RETROFLEX
from athena.lexicon import en_lexicon
from athena.verifier.english import SPLIT_MARKER
from athena.verifier.nepali import DecomposeError, decompose

N_MISTAKES = 2
MAX_SENTENCES = 4

_SWAP: dict[str, list[tuple[str, str]]] = {}
for kinds, kind in ((ASPIRATION, "aspiration"), (RETROFLEX, "retroflex_dental")):
    for a, b in kinds:
        _SWAP.setdefault(a, []).append((b, kind))
        _SWAP.setdefault(b, []).append((a, kind))

EN_VOWELS = "aeiou"
EN_DIGRAPHS = ("sh", "ch", "th")


def ne_changes(word: str) -> list[tuple[str, str, str]]:
    """(cat's word, kind, the letter that changed) for every audible one-letter change."""
    try:
        aks = decompose(word)
    except DecomposeError:
        return []
    if "".join(a.text for a in aks) != word:
        return []
    out = []
    for i, a in enumerate(aks):
        rebuilt = lambda t: "".join(x.text if j != i else t for j, x in enumerate(aks))  # noqa: E731
        if a.kind == "consonant":
            for other, kind in _SWAP.get(a.base, []):
                out.append((rebuilt(a.text.replace(a.base, other, 1)), kind, a.base))
            if a.matra == "ा":
                out.append((rebuilt(a.text.replace("ा", "", 1)), "vowel_sign", "ा"))
            elif a.matra is None and not a.has_halanta and not a.modifiers and i > 0:
                out.append((rebuilt(a.text + "ा"), "vowel_sign", "ा"))
    return [o for o in out if o[0] != word]


def en_changes(word: str) -> list[tuple[str, str, str]]:
    """From the phonics lexicon's spelling units, so only real sounds change: "may" (ay) and
    "far" (ar) are not short vowels; tricky words are left alone."""
    w = word.lower()
    entry = en_lexicon().get(w)
    if not entry or not entry.graphemes:
        return []
    g = [x for x in entry.graphemes if x != SPLIT_MARKER]
    if "".join(g) != w:  # split digraphs (cake) and anything unusual: leave it
        return []
    out = []
    if g[0] in ("b", "d") and len(g) > 1:
        out.append((("d" if g[0] == "b" else "b") + w[1:], "b_d", g[0]))
    if len(g) == 3 and g[1] in EN_VOWELS and len(g[0]) == len(g[2]) == 1 and g[0] not in EN_VOWELS and g[2] not in EN_VOWELS + "rwy":
        other = EN_VOWELS[(EN_VOWELS.index(g[1]) + 2) % 5]  # cat -> cot, pin -> pun
        out.append((g[0] + other + g[2], "short_vowel", g[1]))
    for i, x in enumerate(g):
        if x in EN_DIGRAPHS:
            out.append(("".join(g[:i]) + x[0] + "".join(g[i + 1:]), "digraph", x))
            break
    return [o for o in out if o[0] != w]


def plan_mistakes(
    language: str,
    words: list[str],
    skip: set[str],
    prefer_kinds: list[str],
    practising: set[str],
    rng: random.Random,
) -> list[dict]:
    """Up to N_MISTAKES changes: [{index, word, cat_word, kind, unit}], best targets first.
    The child's own confusion kinds rank first, then changes touching a practised unit."""
    changes = ne_changes if language == "ne" else en_changes
    cands = []
    for i, w in enumerate(words):
        if w in skip or len(w) < 2:
            continue
        for cat_word, kind, unit in changes(w):
            rank = prefer_kinds.index(kind) if kind in prefer_kinds else len(prefer_kinds)
            practised = unit in practising
            cands.append((rank, not practised, rng.random(), {"index": i, "word": w, "cat_word": cat_word,
                                                               "kind": kind, "unit": unit}))
    cands.sort(key=lambda c: c[:3])
    chosen: list[dict] = []
    for *_, c in cands:
        if all(abs(c["index"] - x["index"]) > 1 for x in chosen):  # spread out, one per word
            chosen.append(c)
        if len(chosen) == N_MISTAKES:
            break
    return sorted(chosen, key=lambda c: c["index"])


def cat_sentences(language: str, sentences: list[str], chunk_tokens: list[list[int]], words: list[str],
                  mistakes: list[dict]) -> list[str]:
    """The story as the cat reads it. chunk_tokens: per sentence, per whitespace chunk, the
    token indices it covers (api.display_words). A chunk changes only if it is one word."""
    by_index = {m["index"]: m["cat_word"] for m in mistakes}
    out = []
    for sentence, chunks in zip(sentences, chunk_tokens):
        parts = sentence.split()
        for j, idx in enumerate(chunks):
            if len(idx) == 1 and idx[0] in by_index:
                tok, new = words[idx[0]], by_index[idx[0]]
                pos = parts[j].lower().find(tok.lower())
                if pos >= 0:
                    if parts[j][pos:pos + 1].isupper():
                        new = new[:1].upper() + new[1:]
                    parts[j] = parts[j][:pos] + new + parts[j][pos + len(tok):]
        out.append(" ".join(parts))
    return out


# --- maths: the cat answers first ----------------------------------------------------------

CAT_EVERY = 4  # every 4th maths problem
CAT_RIGHT_EVERY = 3  # 1 in 3 cat answers is right, so the child has to check, not just say "no"


def cat_answer(a: int, b: int, op: str, mistakes: dict[str, int], n: int, rng: random.Random) -> int:
    """The cat's answer: sometimes right; otherwise the child's own kind of mistake."""
    right = a + b if op == "+" else a - b
    if n % CAT_RIGHT_EVERY == 0:
        return right
    if mistakes.get("wrong_operation", 0) > mistakes.get("off_by_one", 0):
        other = a - b if op == "+" else a + b
        if other >= 0 and other != right:
            return other
    return right + 1 if right == 0 or rng.random() < 0.5 else right - 1


def teach_summary(events: list[dict], language: str) -> dict | None:
    """For parents: rounds played, the cat's mistakes caught, and kinds the child let through."""
    rounds = {e["story_id"]: e for e in events if e.get("type") == "teach" and e.get("lang") == language}
    if not rounds:
        return None
    caught: set[tuple[str, int]] = {(e["story_id"], e["index"]) for e in events
                                   if e.get("type") == "teach_tap" and e.get("caught") and e["story_id"] in rounds}
    total, missed = 0, {}
    for tid, r in rounds.items():
        for m in r["mistakes"]:
            total += 1
            if (tid, m["index"]) not in caught:
                missed[m["kind"]] = missed.get(m["kind"], 0) + 1
    return {"rounds": len(rounds), "mistakes": total, "caught": len(caught), "missed_kinds": missed}

"""Build data/en_lexicon.json from the hand-segmented sources.

data/en_lexicon_src.txt   graphemes joined by "." (sh.i.p); a following "+s" token also adds the plural/3sg
data/en_tricky.txt        one tricky word per line, optionally followed by its segmentation
"""

import json
from collections import Counter
from pathlib import Path

from athena.verifier.english import GRAPHEME_PHASE, SPLIT_MARKER, spell

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "data" / "en_lexicon_src.txt"
TRICKY = ROOT / "data" / "en_tricky.txt"
OUT = ROOT / "data" / "en_lexicon.json"

NO_PLAIN_S = {"s", "ss", "x", "sh", "ch", "tch", "z", "zz", "y", "ed"}


def tokens(path: Path):
    for n, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        line = line.split("#", 1)[0]
        for tok in line.split():
            yield n, tok


def parse(seg: str, where: str) -> tuple[str, ...]:
    gs = tuple(seg.split("."))
    for g in gs:
        if g != SPLIT_MARKER and g not in GRAPHEME_PHASE:
            raise SystemExit(f"{where}: unknown grapheme {g!r} in {seg}")
    if sum(g.endswith(SPLIT_MARKER) and g != SPLIT_MARKER for g in gs) != gs.count(SPLIT_MARKER):
        raise SystemExit(f"{where}: unpaired split digraph in {seg}")
    return gs


def phase(gs: tuple[str, ...] | None) -> int | None:
    return max(GRAPHEME_PHASE[g] for g in gs if g != SPLIT_MARKER) if gs else None


def main() -> None:
    entries: dict[str, dict] = {}

    def add(gs: tuple[str, ...], where: str) -> None:
        word = spell(gs)
        if word in entries:
            raise SystemExit(f"{where}: duplicate {word}")
        entries[word] = {"word": word, "graphemes": list(gs), "is_tricky": False}

    last: tuple[str, ...] | None = None
    for n, tok in tokens(SRC):
        where = f"{SRC.name}:{n}"
        if tok == "+s":
            if last is None or last[-1] in NO_PLAIN_S:
                raise SystemExit(f"{where}: +s not valid after {last}")
            add(last + ("s",), where)
            continue
        last = parse(tok, where)
        add(last, where)

    for n, line in enumerate(TRICKY.read_text(encoding="utf-8").splitlines(), 1):
        parts = line.split("#", 1)[0].split()
        if not parts:
            continue
        word = parts[0].lower()
        gs = parse(parts[1], f"{TRICKY.name}:{n}") if len(parts) > 1 else None
        if gs and spell(gs) != word:
            raise SystemExit(f"{TRICKY.name}:{n}: {parts[1]} spells {spell(gs)}, not {word}")
        e = entries.setdefault(word, {"word": word, "graphemes": list(gs) if gs else None, "is_tricky": True})
        e["is_tricky"] = True

    out = []
    for word in sorted(entries):
        e = entries[word]
        gs = tuple(e["graphemes"]) if e["graphemes"] else None
        out.append({**e, "phase": phase(gs)})
    OUT.write_text("\n".join(["["] + [json.dumps(e, ensure_ascii=False) + "," for e in out[:-1]]
                             + [json.dumps(out[-1], ensure_ascii=False), "]"]) + "\n", encoding="utf-8")

    print(f"{len(out)} words -> {OUT.relative_to(ROOT)}  (tricky: {sum(e['is_tricky'] for e in out)})")
    print("by phase:", dict(sorted(Counter(e["phase"] for e in out if e["phase"]).items())))
    used = Counter(g for e in out for g in (e["graphemes"] or []) if g != SPLIT_MARKER)
    unused = sorted(set(GRAPHEME_PHASE) - set(used))
    print("graphemes never used:", unused or "none")


if __name__ == "__main__":
    main()

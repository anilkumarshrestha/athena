"""Readable words vs units known: greedy unlock order vs plain teaching order.

  python scripts/coverage_curve.py            # both languages, writes eval/results/coverage_<lang>.csv

Starts from a small base set and adds one unit at a time. "teaching" follows the
varnamala / phonics sequence as-is; "unlock" picks, within the next WINDOW units of
that sequence, the one that makes the most new words readable (athena.progression).
"""

import csv
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from athena.mastery import UnitState  # noqa: E402
from athena.progression import SEQUENCE, next_units, readable_count  # noqa: E402

OUT = Path(__file__).resolve().parent.parent / "eval" / "results"
BASE = {"ne": ["c:अ", "c:आ", "c:क", "c:म", "m:ा"], "en": ["g:s", "g:a", "g:t"]}
STEPS = {"ne": 40, "en": 30}


def curve(lang: str, greedy: bool) -> list[tuple[int, str, int]]:
    units = {s: UnitState("mastered", 3, 3) for s in BASE[lang]}
    rows = []
    for step in range(STEPS[lang]):
        if greedy:
            nxt = next_units(lang, units, k=1)
        else:
            nxt = [s for s in SEQUENCE[lang] if s not in units][:1]
        if not nxt:
            break
        units[nxt[0]] = UnitState("mastered", 3, 3)
        known = frozenset(units)
        rows.append((len(known), nxt[0].split(":", 1)[1], readable_count(lang, known)))
    return rows


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    for lang in ("ne", "en"):
        teach, unlock = curve(lang, False), curve(lang, True)
        path = OUT / f"coverage_{lang}.csv"
        with path.open("w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(["units_known", "teaching_next", "teaching_words", "unlock_next", "unlock_words"])
            for (n, tu, tw), (_, uu, uw) in zip(teach, unlock):
                w.writerow([n, tu, tw, uu, uw])
        print(f"\n{lang}: units  teaching-order  unlock-order   -> {path.relative_to(OUT.parent.parent)}")
        for (n, tu, tw), (_, uu, uw) in list(zip(teach, unlock))[4::5]:
            print(f"   {n:3d}   {tw:5d} (+{tu:<4})  {uw:5d} (+{uu})")


if __name__ == "__main__":
    main()

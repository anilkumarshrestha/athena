"""Tag data/ne_seed_words.txt with akshara units + signatures -> data/ne_seed.json."""

import json
from collections import Counter
from pathlib import Path

from athena.verifier.nepali import decompose, normalize

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "data" / "ne_seed_words.txt"
OUT = ROOT / "data" / "ne_seed.json"


def main() -> None:
    entries: list[dict] = []
    seen: set[str] = set()
    category = "misc"
    for line in SRC.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        if line.startswith("#"):
            name = line[1:].strip()
            if " " not in name:
                category = name
            continue
        for word in map(normalize, line.split()):
            if word in seen:
                raise SystemExit(f"duplicate word: {word}")
            seen.add(word)
            units = decompose(word)  # raises on malformed input: fix the source file
            sigs = sorted(set().union(*(u.signatures() for u in units)))
            entries.append(
                {"word": word, "category": category, "units": [u.text for u in units], "signatures": sigs}
            )

    OUT.write_text(json.dumps(entries, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")

    sig_counts = Counter(s for e in entries for s in e["signatures"])
    by_kind = Counter(s[0] for s in sig_counts)
    print(f"{len(entries)} words -> {OUT.relative_to(ROOT)}")
    print(f"distinct signatures: {len(sig_counts)}  (c={by_kind['c']} m={by_kind['m']} k={by_kind['k']})")
    print("categories:", dict(Counter(e["category"] for e in entries)))


if __name__ == "__main__":
    main()

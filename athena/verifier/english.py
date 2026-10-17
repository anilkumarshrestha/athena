"""English verifier: closed vocabulary over a pre-tagged lexicon.

English spelling is opaque, so we never segment unseen words. A word must be in
the lexicon, and then either every grapheme is mastered, or it is a tricky word
that has been explicitly taught (w:<word>).

Graphemes are spelling units in synthetic-phonics order (Letters and Sounds
style). A split digraph is tagged at the vowel ("a_e") with a "_e" marker where
the silent e sits; only the vowel tag is a mastery unit.
"""

import json
import re
from dataclasses import dataclass
from pathlib import Path

from athena.verifier.base import VerifyResult, Violation

_PHASES: dict[int, str] = {
    2: "s a t p i n m d g o c k ck e u r h b f ff l ll ss",
    3: "j v w x y z zz qu ch sh th ng ai ee igh oa oo ar or ur ow oi ear air ure er",
    4: "bb dd gg mm nn pp rr tt ed",
    5: "ay ou ie ea oy ir ue aw wh ph ew oe au ey a_e e_e i_e o_e u_e",
    6: "tch dge kn wr mb",
}
GRAPHEME_PHASE: dict[str, int] = {g: p for p, gs in _PHASES.items() for g in gs.split()}
SPLIT_MARKER = "_e"

_WORD = re.compile(r"[a-z]+(?:'[a-z]+)?")


@dataclass(frozen=True)
class LexEntry:
    graphemes: tuple[str, ...] | None  # None: tricky word with no decodable reading
    is_tricky: bool


def spell(graphemes: tuple[str, ...]) -> str:
    out = []
    for g in graphemes:
        if g == SPLIT_MARKER:
            out.append("e")
        elif g.endswith(SPLIT_MARKER):
            out.append(g[0])
        else:
            out.append(g)
    return "".join(out)


def grapheme_signatures(graphemes: tuple[str, ...]) -> list[str]:
    sigs: list[str] = []
    for g in graphemes:
        sig = "g:" + g
        if g != SPLIT_MARKER and sig not in sigs:
            sigs.append(sig)
    return sigs


def load_lexicon(path: Path) -> dict[str, LexEntry]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    return {
        e["word"]: LexEntry(tuple(e["graphemes"]) if e["graphemes"] else None, e["is_tricky"]) for e in raw
    }


def tokenize(text: str) -> list[str]:
    return _WORD.findall(text.lower().replace("’", "'"))


class EnglishVerifier:
    language = "en"

    def __init__(
        self,
        mastery: frozenset[str],
        lexicon: dict[str, LexEntry],
        allowed_words: frozenset[str] = frozenset(),
    ) -> None:
        self.mastery = mastery
        self.lexicon = lexicon
        self.allowed_words = frozenset(w.lower() for w in allowed_words)

    def verify(self, text: str) -> VerifyResult:
        violations: list[Violation] = []
        used: set[str] = set()
        words = tokenize(text)
        for idx, word in enumerate(words):
            if word in self.allowed_words:
                continue
            entry = self.lexicon.get(word)
            if entry is None:
                violations.append(Violation(word, idx, None, "not in lexicon"))
                continue
            sigs = grapheme_signatures(entry.graphemes) if entry.graphemes else []
            missing = [s for s in sigs if s not in self.mastery]
            if entry.graphemes and not missing:
                used.update(sigs)
            elif entry.is_tricky:
                tricky = "w:" + word
                if tricky in self.mastery:
                    used.add(tricky)
                else:
                    violations.append(Violation(word, idx, tricky, "tricky word not taught"))
            else:
                violations.extend(Violation(word, idx, s, "not mastered") for s in missing)
        return VerifyResult(
            ok=not violations,
            violations=tuple(violations),
            words_checked=len(words),
            units_used=frozenset(used),
        )

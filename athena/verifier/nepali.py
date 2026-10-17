"""Nepali (Devanagari) verifier: open vocabulary, algorithmic decomposition.

Devanagari is an abugida, so the unit is the akshara, not the letter. Each
akshara maps to mastery signatures:

  c:<x>  consonant or independent vowel
  m:<x>  matra (vowel sign), modifier (ं ँ ः), or halanta (्)
  k:<x>  conjunct, mastered as a whole; its parts are NOT required separately
"""

import re
import unicodedata
from dataclasses import dataclass
from typing import Literal

from athena.verifier.base import VerifyResult, Violation

NUKTA = "़"
VIRAMA = "्"
ZW_CHARS = dict.fromkeys(map(ord, "‌‍"))

# Splits words; anything else that survives must decompose cleanly.
_WORD_SPLIT = re.compile(r"[\s।॥,.?!;:\"'“”‘’()\[\]\-—–…]+")


def _in(ch: str, *ranges: tuple[int, int]) -> bool:
    o = ord(ch)
    return any(lo <= o <= hi for lo, hi in ranges)


def is_consonant(ch: str) -> bool:
    return _in(ch, (0x0915, 0x0939), (0x0958, 0x095F), (0x0978, 0x097F))


def is_independent_vowel(ch: str) -> bool:
    return _in(ch, (0x0904, 0x0914), (0x0960, 0x0961), (0x0972, 0x0977))


def is_matra(ch: str) -> bool:
    return _in(
        ch,
        (0x093A, 0x093B),
        (0x093E, 0x094C),
        (0x094E, 0x094F),
        (0x0955, 0x0957),
        (0x0962, 0x0963),
    )


def is_modifier(ch: str) -> bool:
    return _in(ch, (0x0900, 0x0903))


class DecomposeError(ValueError):
    pass


@dataclass(frozen=True)
class Akshara:
    text: str
    base: str  # consonant, full conjunct (with viramas), or independent vowel
    kind: Literal["consonant", "conjunct", "vowel"]
    conjunct_parts: tuple[str, ...] | None
    matra: str | None
    modifiers: tuple[str, ...]
    has_halanta: bool

    def signatures(self) -> frozenset[str]:
        sigs = {("k:" if self.kind == "conjunct" else "c:") + self.base}
        if self.matra:
            sigs.add("m:" + self.matra)
        sigs.update("m:" + m for m in self.modifiers)
        if self.has_halanta:
            sigs.add("m:" + VIRAMA)
        return frozenset(sigs)


def normalize(text: str) -> str:
    return unicodedata.normalize("NFC", text).translate(ZW_CHARS)


def decompose(word: str) -> list[Akshara]:
    s = normalize(word)
    n = len(s)
    units: list[Akshara] = []
    i = 0

    def take_consonant() -> str:
        nonlocal i
        c = s[i]
        i += 1
        if i < n and s[i] == NUKTA:
            c += NUKTA
            i += 1
        return c

    while i < n:
        start = i
        ch = s[i]
        matra = None
        halanta = False

        if is_consonant(ch):
            parts = [take_consonant()]
            while i < n and s[i] == VIRAMA:
                if i + 1 < n and is_consonant(s[i + 1]):
                    i += 1
                    parts.append(take_consonant())
                else:
                    halanta = True
                    i += 1
                    break
            if not halanta and i < n and is_matra(s[i]):
                matra = s[i]
                i += 1
            if len(parts) > 1:
                kind = "conjunct"
                base = VIRAMA.join(parts)
                conjunct_parts = tuple(parts)
            else:
                kind = "consonant"
                base = parts[0]
                conjunct_parts = None
        elif is_independent_vowel(ch):
            i += 1
            kind = "vowel"
            base = ch
            conjunct_parts = None
        else:
            raise DecomposeError(f"unexpected {ch!r} (U+{ord(ch):04X}) at {i} in {word!r}")

        mods = []
        while i < n and is_modifier(s[i]):
            mods.append(s[i])
            i += 1

        units.append(
            Akshara(
                text=s[start:i],
                base=base,
                kind=kind,
                conjunct_parts=conjunct_parts,
                matra=matra,
                modifiers=tuple(mods),
                has_halanta=halanta,
            )
        )
    return units


def tokenize(text: str) -> list[str]:
    return [w for w in _WORD_SPLIT.split(normalize(text)) if w]


class NepaliVerifier:
    language = "ne"

    def __init__(self, mastery: frozenset[str], allowed_words: frozenset[str] = frozenset()) -> None:
        self.mastery = mastery
        self.allowed_words = frozenset(normalize(w) for w in allowed_words)

    def verify(self, text: str) -> VerifyResult:
        violations: list[Violation] = []
        used: set[str] = set()
        words = tokenize(text)
        for idx, word in enumerate(words):
            if word in self.allowed_words:
                continue
            try:
                units = decompose(word)
            except DecomposeError as e:
                violations.append(Violation(word, idx, None, str(e)))
                continue
            sigs: list[str] = []
            for u in units:
                for sig in sorted(u.signatures()):
                    if sig not in sigs:
                        sigs.append(sig)
            used.update(sigs)
            violations.extend(
                Violation(word, idx, sig, "not mastered") for sig in sigs if sig not in self.mastery
            )
        return VerifyResult(
            ok=not violations,
            violations=tuple(violations),
            words_checked=len(words),
            units_used=frozenset(used),
        )

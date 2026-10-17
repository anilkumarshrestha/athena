"""Verifier interface. Pure stdlib: this is the guarantee, no model in the loop."""

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class Violation:
    word: str
    word_index: int
    unit: str | None  # signature that is not mastered; None if the word is malformed/unknown
    reason: str


@dataclass(frozen=True)
class VerifyResult:
    ok: bool
    violations: tuple[Violation, ...]
    words_checked: int
    units_used: frozenset[str]


class Verifier(Protocol):
    language: str
    mastery: frozenset[str]

    def verify(self, text: str) -> VerifyResult: ...

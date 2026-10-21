"""Reading level 1-10: how much of a language's letters/sounds a child has mastered. Pure code,
shown on the child's home and in grown-up views.

Ten equal steps of the teaching order (progression.SEQUENCE): level 2 at 10% mastered, ...,
level 10 at 90%. Story difficulty still adapts through the story-size band
(progression.LEVELS, 1-3); the reading level tells the child and grown-ups how far they have
come and how close the next level is.
"""

from dataclasses import dataclass

from athena.mastery import UnitState
from athena.progression import SEQUENCE

LEVELS = 10
NAMES = [f"Level {i}" for i in range(1, LEVELS + 1)]
CUTS = [i / LEVELS for i in range(LEVELS)]  # share of the teaching order mastered to reach each level


@dataclass(frozen=True)
class Stage:
    n: int  # 1..10
    name: str
    mastered: int  # units of the teaching order mastered
    start: int  # mastered units where this stage starts
    next_at: int  # mastered units for the next level (level 10: all of them)
    total: int  # units in the teaching order

    @property
    def next_name(self) -> str | None:
        return NAMES[self.n] if self.n < len(NAMES) else None


def threshold(i: int, total: int) -> int:
    """Mastered units needed to reach stage i+1 (0-based i)."""
    return round(CUTS[i] * total)


def stage(language: str, units: dict[str, UnitState]) -> Stage:
    order = SEQUENCE[language]
    total = len(order)
    mastered = sum(1 for sig in order if (u := units.get(sig)) and u.state == "mastered")
    i = max(k for k in range(len(CUTS)) if mastered >= threshold(k, total))
    nxt = threshold(i + 1, total) if i + 1 < len(CUTS) else total  # level 10: on to every letter
    return Stage(i + 1, NAMES[i], mastered, threshold(i, total), nxt, total)

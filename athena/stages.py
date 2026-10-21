"""Reading stages: a child-friendly name for how much of a language's letters/sounds a child
has mastered. Pure code, shown on the child's home and in grown-up views.

Five stages by the share of the teaching order (progression.SEQUENCE) mastered. Names are
English for every language (also on Nepali tiles). Story difficulty still adapts through the
story-size level (progression.LEVELS); a stage only tells the child and grown-ups how far
they have come and how close the next stage is.
"""

from dataclasses import dataclass

from athena.mastery import UnitState
from athena.progression import SEQUENCE

NAMES = ["Sprout", "Leaf", "Flower", "Tree", "Forest"]
CUTS = [0.0, 0.15, 0.35, 0.60, 0.85]  # share of the teaching order mastered to reach each stage


@dataclass(frozen=True)
class Stage:
    n: int  # 1..5
    name: str
    mastered: int  # units of the teaching order mastered
    start: int  # mastered units where this stage starts
    next_at: int | None  # mastered units for the next stage; None at the last stage
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
    nxt = threshold(i + 1, total) if i + 1 < len(CUTS) else None
    return Stage(i + 1, NAMES[i], mastered, threshold(i, total), nxt, total)

"""Mastery model per learner and language. Pure stdlib; explainable on purpose.

PLAN §5 rule, applied once per reading session:
  - unit correct in 3 sessions running (and seen >= 3 times) -> mastered
  - unit wrong twice in one session                         -> practicing (demoted)
  - one error in a session resets the streak, no demotion

Stories may use mastered units and practicing units. A demoted unit sits out the
next story (cooldown 1), then returns as a practice target, so it is re-taught
rather than avoided forever. Unseen units never appear in stories.
"""

from dataclasses import dataclass
from typing import Literal

State = Literal["mastered", "practicing", "unseen", "excluded"]

MASTER_STREAK = 3
MIN_SEEN = 3
DEMOTE_ERRORS = 2
COOLDOWN_SESSIONS = 1


@dataclass
class UnitState:
    state: State
    streak: int = 0  # consecutive sessions with the unit read correctly
    seen: int = 0  # sessions in which the unit appeared
    cooldown: int = 0  # sessions to sit out after a demotion


@dataclass(frozen=True)
class Change:
    unit: str
    before: State
    after: State


def allowed(units: dict[str, UnitState]) -> frozenset[str]:
    """Signatures a story may use right now."""
    return frozenset(
        sig for sig, u in units.items() if u.state == "mastered" or (u.state == "practicing" and u.cooldown == 0)
    )


def practice_targets(units: dict[str, UnitState]) -> list[str]:
    return sorted(sig for sig, u in units.items() if u.state == "practicing" and u.cooldown == 0)


def apply_session(
    units: dict[str, UnitState], unit_correct: dict[str, int], unit_errors: dict[str, int]
) -> list[Change]:
    """Update units in place from one reading; return the state changes."""
    changes: list[Change] = []
    demoted: set[str] = set()

    for sig in sorted(set(unit_correct) | set(unit_errors)):
        u = units.setdefault(sig, UnitState("practicing"))
        before = u.state
        errors = unit_errors.get(sig, 0)
        u.seen += 1
        if errors >= DEMOTE_ERRORS:
            u.state, u.streak, u.cooldown = "practicing", 0, COOLDOWN_SESSIONS
            demoted.add(sig)
        elif errors == 1:
            u.streak = 0
        else:
            u.streak += 1
            if u.state == "practicing" and u.streak >= MASTER_STREAK and u.seen >= MIN_SEEN:
                u.state = "mastered"
        if u.state != before:
            changes.append(Change(sig, before, u.state))

    # A session passed: units sitting out (not just demoted) come back.
    for sig, u in units.items():
        if u.cooldown and sig not in demoted:
            u.cooldown -= 1
    return changes

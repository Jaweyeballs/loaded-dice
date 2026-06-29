"""Core dice mechanics for the Yahtzee engine.

A DiceSet holds 5 Die objects. Locked dice are skipped on reroll,
matching standard Yahtzee keep/reroll behavior. This covers M0 Group A
from the project roadmap.
"""

import random


class Die:
    """A single six-sided die that can be locked between rolls."""

    def __init__(self, value: int = 1):
        self.value = value
        self.locked = False

    def roll(self) -> int:
        """Roll this die, unless it is locked. Returns the resulting value."""
        if not self.locked:
            self.value = random.randint(1, 6)
        return self.value

    def __repr__(self) -> str:
        state = "locked" if self.locked else "open"
        return f"Die(value={self.value}, {state})"


class TooManyRollsError(Exception):
    """Raised when a DiceSet tries to roll more times than allowed in a turn."""


class DiceSet:
    """Five dice plus the roll-count enforcement for a single turn."""

    MAX_ROLLS_PER_TURN = 3

    def __init__(self, size: int = 5):
        self.dice = [Die() for _ in range(size)]
        self.rolls_this_turn = 0

    def roll(self) -> list[int]:
        """Roll all unlocked dice. Raises TooManyRollsError past the per-turn limit."""
        if self.rolls_this_turn >= self.MAX_ROLLS_PER_TURN:
            raise TooManyRollsError(
                f"Already rolled {self.rolls_this_turn} times this turn "
                f"(max {self.MAX_ROLLS_PER_TURN})."
            )
        for die in self.dice:
            die.roll()
        self.rolls_this_turn += 1
        return self.values

    def lock(self, index: int) -> None:
        self.dice[index].locked = True

    def unlock(self, index: int) -> None:
        self.dice[index].locked = False

    @property
    def values(self) -> list[int]:
        return [die.value for die in self.dice]

    def reset_for_new_turn(self) -> None:
        """Unlock every die and reset the roll counter — call at the start of each turn."""
        self.rolls_this_turn = 0
        for die in self.dice:
            die.locked = False

    def __repr__(self) -> str:
        return f"DiceSet({self.dice})"

"""Core dice mechanics for the Yahtzee engine.

A DiceSet holds one or more Die objects (default 5). Locked dice are skipped on
reroll, matching standard Yahtzee keep/reroll behavior. Default is 3 rolls per
turn; card effects may grant more. Card effects may also add extra dice;
scoring always uses 5 selected values (see GDD). Standard dice use faces 1–6;
special dice (e.g. The Coin's blank faces) may use 0 or other face sets when
card effects are implemented.
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


def bump_die_face(value: int) -> int:
    """Increase a standard die face by 1, wrapping 6 → 1 (Icarus)."""
    if value < 1 or value > 6:
        raise ValueError(f"Standard die face must be 1–6, got {value}")
    return (value % 6) + 1


class TooManyRollsError(Exception):
    """Raised when a DiceSet tries to roll more times than allowed in a turn."""


DEFAULT_MAX_ROLLS_PER_TURN = 3


class DiceSet:
    """Dice for a single turn. Default size is 5; card effects may increase it."""

    def __init__(self, size: int = 5, max_rolls: int = DEFAULT_MAX_ROLLS_PER_TURN):
        self.dice = [Die() for _ in range(size)]
        self.standard_max_rolls = max_rolls
        self.max_rolls = max_rolls
        self.rolls_this_turn = 0

    def grant_extra_rolls(self, count: int = 1) -> None:
        """Increase the per-turn roll limit (e.g. The Gambler, The Toddler)."""
        self.max_rolls += count
        # standard_max_rolls stays fixed — only ability-free rolls earn chip income.

    def roll(self) -> list[int]:
        """Roll all unlocked dice. Raises TooManyRollsError past the per-turn limit."""
        if self.rolls_this_turn >= self.max_rolls:
            raise TooManyRollsError(
                f"Already rolled {self.rolls_this_turn} times this turn "
                f"(max {self.max_rolls})."
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

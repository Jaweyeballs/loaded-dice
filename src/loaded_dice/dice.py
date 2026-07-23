"""Core dice mechanics for the Yahtzee engine.

A DiceSet holds one or more Die objects (default 5). Locked dice are skipped on
reroll, matching standard Yahtzee keep/reroll behavior. Default is 3 rolls per
turn; card effects may grant more. Card effects may also add extra dice;
scoring always uses 5 selected values (see GDD). Standard dice use faces 1–6;
special dice (e.g. Boolean blanks, Benchwarmer 1–3) may use other face sets.
"""

from __future__ import annotations

import random

STANDARD_FACES = (1, 2, 3, 4, 5, 6)
BENCHWARMER_FACES = (1, 2, 3)
BOOLEAN_FACES = (6, 6, 6, 0, 0, 0)


class Die:
    """A die that can be locked between rolls; faces may be non-standard."""

    def __init__(
        self,
        value: int = 1,
        faces: tuple[int, ...] | list[int] | None = None,
        *,
        kind: str = "standard",
    ):
        self.faces = tuple(faces) if faces is not None else STANDARD_FACES
        if not self.faces:
            raise ValueError("Die must have at least one face")
        self.value = value if value in self.faces else self.faces[0]
        self.locked = False
        # Visual/source tag for HUD tinting (benchwarmer, boolean, …).
        self.kind = kind

    def roll(self) -> int:
        """Roll this die, unless it is locked. Returns the resulting value."""
        if not self.locked:
            self.value = random.choice(self.faces)
        return self.value

    def __repr__(self) -> str:
        state = "locked" if self.locked else "open"
        return f"Die(value={self.value}, {state})"


def bump_die_face(value: int) -> int:
    """Increase a standard die face by 1, wrapping 6 → 1 (Icarus)."""
    if value < 1 or value > 6:
        raise ValueError(f"Standard die face must be 1–6, got {value}")
    return (value % 6) + 1


def bump_die(die: Die) -> None:
    """Bump a die's showing face by one within its face set when possible (wraps)."""
    if die.value in STANDARD_FACES and set(die.faces) >= set(STANDARD_FACES):
        die.value = bump_die_face(die.value)
        return
    # Non-standard: step to the next distinct face value in sorted unique faces.
    unique = sorted(set(die.faces))
    try:
        idx = unique.index(die.value)
    except ValueError:
        die.value = unique[0]
        return
    die.value = unique[(idx + 1) % len(unique)]


def raise_die_no_wrap(die: Die) -> None:
    """Increase a die's face by one without wrapping (Super serum: 6 stays 6)."""
    unique = sorted(set(die.faces))
    try:
        idx = unique.index(die.value)
    except ValueError:
        return
    if idx + 1 < len(unique):
        die.value = unique[idx + 1]


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
        # Psychic: next unlocked roll for these indices uses the queued face.
        self._forced_next_values: dict[int, int] = {}
        # Twins: follower_index → leader_index; follower copies leader on next roll.
        self._twins_links: dict[int, int] = {}

    def grant_extra_rolls(self, count: int = 1) -> None:
        """Increase the per-turn roll limit (e.g. The Gambler, The Toddler)."""
        self.max_rolls += count
        # standard_max_rolls stays fixed — only ability-free rolls earn chip income.

    def add_die(
        self,
        faces: tuple[int, ...] | list[int],
        *,
        value: int | None = None,
        locked: bool = False,
        kind: str = "standard",
    ) -> int:
        """Append a die and return its index (Benchwarmer, Boolean, etc.)."""
        die = Die(
            value=value if value is not None else faces[0],
            faces=faces,
            kind=kind,
        )
        die.locked = locked
        self.dice.append(die)
        return len(self.dice) - 1

    def queue_forced_roll(self, index: int, value: int) -> None:
        """Force the next roll of die *index* to *value* (Psychic)."""
        if index < 0 or index >= len(self.dice):
            raise IndexError(f"Invalid die index: {index}")
        die = self.dice[index]
        if value not in die.faces:
            raise ValueError(f"Face {value} not on die faces {die.faces}")
        self._forced_next_values[index] = value

    def queue_twins(self, leader_index: int, follower_index: int) -> None:
        """On the next roll, *follower* becomes whatever *leader* shows."""
        size = len(self.dice)
        if leader_index < 0 or leader_index >= size:
            raise IndexError(f"Invalid die index: {leader_index}")
        if follower_index < 0 or follower_index >= size:
            raise IndexError(f"Invalid die index: {follower_index}")
        if leader_index == follower_index:
            raise ValueError("Twins requires two different dice")
        self._twins_links[follower_index] = leader_index

    @property
    def forced_next_values(self) -> dict[int, int]:
        return dict(self._forced_next_values)

    @property
    def twins_links(self) -> dict[int, int]:
        return dict(self._twins_links)

    def roll(self) -> list[int]:
        """Roll all unlocked dice. Raises TooManyRollsError past the per-turn limit."""
        if self.rolls_this_turn >= self.max_rolls:
            raise TooManyRollsError(
                f"Already rolled {self.rolls_this_turn} times this turn "
                f"(max {self.max_rolls})."
            )
        twins = dict(self._twins_links)
        self._twins_links.clear()
        for index, die in enumerate(self.dice):
            if die.locked:
                continue
            # Twins followers skip their own roll; they copy the leader after.
            if index in twins:
                continue
            forced = self._forced_next_values.pop(index, None)
            if forced is not None:
                die.value = forced
            else:
                die.roll()
        for follower_index, leader_index in twins.items():
            follower = self.dice[follower_index]
            if follower.locked:
                continue
            face = self.dice[leader_index].value
            if face in follower.faces:
                follower.value = face
            else:
                # Leader face not on follower (e.g. Boolean blanks) — roll normally.
                follower.roll()
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
        self._forced_next_values.clear()
        self._twins_links.clear()
        for die in self.dice:
            die.locked = False

    def __repr__(self) -> str:
        return f"DiceSet({self.dice})"

"""Chip economy — interest and turn income helpers."""

from __future__ import annotations

from loaded_dice.dice import DEFAULT_MAX_ROLLS_PER_TURN

CHIPS_PER_SCORED_HAND = 300
CHIPS_PER_UNUSED_STANDARD_ROLL = 150

INTEREST_CHIPS_PER_BLOCK = 50
INTEREST_BLOCK_SIZE = 200
MAX_INTEREST_CHIPS = 200

COMPENSATION_PACIFIST_CHIPS = 200
COMPENSATION_CHIPS_PER_ATTACKER = 100


class InsufficientChipsError(Exception):
    """Raised when a player cannot afford a chip cost."""


def calculate_interest(chip_balance: int) -> int:
    """Return interest chips for *chip_balance* (50 per 200 held, max 200)."""
    if chip_balance < 0:
        raise ValueError("Chip balance cannot be negative")
    earned = (chip_balance // INTEREST_BLOCK_SIZE) * INTEREST_CHIPS_PER_BLOCK
    return min(earned, MAX_INTEREST_CHIPS)


def calculate_compensation(
    attackers_on_player: int,
    player_attacked_anyone: bool,
) -> int:
    """Return compensation chips from the previous rotation (GDD §2).

    Pacifist bonus (200) and per-attacker payout (100 each) stack.
    """
    if attackers_on_player < 0:
        raise ValueError("attackers_on_player cannot be negative")
    pacifist = 0 if player_attacked_anyone else COMPENSATION_PACIFIST_CHIPS
    return pacifist + attackers_on_player * COMPENSATION_CHIPS_PER_ATTACKER


def chips_for_unused_standard_rolls(
    rolls_used: int,
    standard_max_rolls: int = DEFAULT_MAX_ROLLS_PER_TURN,
) -> int:
    """Chips for leftover standard rerolls when scoring. Ability-granted rolls excluded."""
    if rolls_used < 0:
        raise ValueError("rolls_used cannot be negative")
    standard_used = min(rolls_used, standard_max_rolls)
    unused = max(0, standard_max_rolls - standard_used)
    return unused * CHIPS_PER_UNUSED_STANDARD_ROLL

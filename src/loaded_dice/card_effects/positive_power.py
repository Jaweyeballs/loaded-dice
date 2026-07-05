"""Positive power card effects — cast on self, resolve immediately."""

from __future__ import annotations

from typing import TYPE_CHECKING, Callable

from loaded_dice.cards import CardId
from loaded_dice.dice import bump_die_face

if TYPE_CHECKING:
    from loaded_dice.match import Match, Player

# --- Constants (balance here) ---

# --- Cast handlers ---


def _icarus_on_cast(player: Player, match: Match, **kwargs) -> None:
    die_index = kwargs.get("die_index")
    if die_index is None:
        raise ValueError("Icarus requires die_index")
    if match.dice is None:
        raise ValueError("No dice set for this turn")
    try:
        die = match.dice.dice[die_index]
    except IndexError as exc:
        raise ValueError(f"Invalid die index: {die_index}") from exc
    die.value = bump_die_face(die.value)


def _parry_on_cast(player: Player, match: Match, **kwargs) -> None:
    # Parry is resolved during TURN_START when the player picks which queued
    # hindrance to block via Match.block_hindrance. Cast marks readiness.
    player.parry_ready = True


# Registry: CardId → handler. Handlers receive (player, match, **kwargs).
# Optional kwargs: die_index (Icarus), target (Helping Hand and similar).
POSITIVE_POWER_CAST: dict[CardId, Callable[..., None]] = {
    CardId.ICARUS: _icarus_on_cast,
    CardId.PARRY: _parry_on_cast,
}


def cast_positive_power(
    card_id: CardId,
    player: Player,
    match: Match,
    **kwargs,
) -> None:
    """Resolve a positive power card cast by *player*."""
    handler = POSITIVE_POWER_CAST.get(card_id)
    if handler is None:
        raise ValueError(f"No positive power handler for {card_id.value}")
    handler(player, match, **kwargs)

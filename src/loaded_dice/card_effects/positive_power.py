"""Positive power card effects — cast on self, resolve immediately."""

from __future__ import annotations

from typing import TYPE_CHECKING, Callable

from loaded_dice.cards import CardId

if TYPE_CHECKING:
    from loaded_dice.match import Match, Player

# --- Constants (balance here) ---

# --- Cast handlers ---


def _icarus_on_cast(player: Player, match: Match, **kwargs) -> None:
    raise NotImplementedError("Icarus is not implemented yet")


def _parry_on_cast(player: Player, match: Match, **kwargs) -> None:
    raise NotImplementedError("Parry is not implemented yet")


# Registry: CardId → handler. Handlers receive (player, match, **kwargs) as needed.
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

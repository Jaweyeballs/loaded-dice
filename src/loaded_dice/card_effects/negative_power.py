"""Negative power card effects — hindrances queued on a target's turn."""

from __future__ import annotations

from typing import TYPE_CHECKING, Callable

from loaded_dice.cards import CardId

if TYPE_CHECKING:
    from loaded_dice.match import Match, Player

# --- Constants (balance here) ---

BLUE_SHELL_POINT_LOSS = 10

# --- Hindrance resolvers (run once when target clicks Start Turn) ---


def _glass_half_full_on_resolve(target: Player, caster: Player, match: Match) -> None:
    target.turn_effects.zero_upper = True


def _glass_half_empty_on_resolve(target: Player, caster: Player, match: Match) -> None:
    target.turn_effects.zero_lower = True


def _blue_shell_on_resolve(target: Player, caster: Player, match: Match) -> None:
    raise NotImplementedError("Blue Shell point deduction is not wired yet")


HINDRANCE_RESOLVERS: dict[CardId, Callable[[Player, Player, Match], None]] = {
    CardId.GLASS_HALF_FULL: _glass_half_full_on_resolve,
    CardId.GLASS_HALF_EMPTY: _glass_half_empty_on_resolve,
    # CardId.BLUE_SHELL: _blue_shell_on_resolve,  # add CardId when implemented
}


def resolve_hindrance(
    card_id: CardId,
    target: Player,
    caster: Player,
    match: Match,
) -> None:
    """Apply a queued hindrance to *target* at turn start."""
    handler = HINDRANCE_RESOLVERS.get(card_id)
    if handler is None:
        raise ValueError(f"No hindrance handler for {card_id.value}")
    handler(target, caster, match)

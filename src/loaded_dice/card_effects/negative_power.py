"""Negative power card effects — hindrances queued on a target's turn."""

from __future__ import annotations

from typing import TYPE_CHECKING, Callable

from loaded_dice.cards import CardId

if TYPE_CHECKING:
    from loaded_dice.match import Match, Player

# --- Constants (balance here) ---

BLUE_SHELL_POINT_LOSS = 10
POSITIVE_PUNISHMENT_POINT_LOSS = 5
NEGATIVE_PUNISHMENT_CHIP_LOSS = 200

# --- Hindrance resolvers (run once when target clicks Start Turn) ---


def _glass_half_full_on_resolve(target: Player, caster: Player, match: Match) -> None:
    target.turn_effects.zero_upper = True


def _glass_half_empty_on_resolve(target: Player, caster: Player, match: Match) -> None:
    target.turn_effects.zero_lower = True


def _blue_shell_on_resolve(target: Player, caster: Player, match: Match) -> None:
    target.lose_points(BLUE_SHELL_POINT_LOSS)


def _already_in_jail_on_resolve(target: Player, caster: Player, match: Match) -> None:
    target.jail_armed = True
    target.jail_locked_index = None


def _positive_punishment_on_resolve(target: Player, caster: Player, match: Match) -> None:
    if match.rotation_count == 0:
        return
    if not match.player_attacked_player_last_rotation(target, caster):
        return
    target.turn_effects.score_penalty += POSITIVE_PUNISHMENT_POINT_LOSS


def _negative_punishment_on_resolve(target: Player, caster: Player, match: Match) -> None:
    if match.rotation_count == 0:
        return
    if not match.player_attacked_player_last_rotation(target, caster):
        return
    target.lose_chips(NEGATIVE_PUNISHMENT_CHIP_LOSS)


HINDRANCE_RESOLVERS: dict[CardId, Callable[[Player, Player, Match], None]] = {
    CardId.GLASS_HALF_FULL: _glass_half_full_on_resolve,
    CardId.GLASS_HALF_EMPTY: _glass_half_empty_on_resolve,
    CardId.POSITIVE_PUNISHMENT: _positive_punishment_on_resolve,
    CardId.NEGATIVE_PUNISHMENT: _negative_punishment_on_resolve,
    CardId.BLUE_SHELL: _blue_shell_on_resolve,
    CardId.ALREADY_IN_JAIL: _already_in_jail_on_resolve,
}

_GLASS_HALF_OPPOSITES: dict[CardId, CardId] = {
    CardId.GLASS_HALF_FULL: CardId.GLASS_HALF_EMPTY,
    CardId.GLASS_HALF_EMPTY: CardId.GLASS_HALF_FULL,
}


class HindranceConflictError(Exception):
    """Raised when a hindrance cannot be queued on the target."""


def validate_hindrance_queue(target: Player, card_id: CardId) -> None:
    """Enforce queue rules before a hindrance is appended to *target*."""
    opposite = _GLASS_HALF_OPPOSITES.get(card_id)
    if opposite is None:
        return
    if any(hindrance.card_id == opposite for hindrance in target.queued_hindrances):
        raise HindranceConflictError(
            "Glass half empty and glass half full cannot both be queued on the same player"
        )


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

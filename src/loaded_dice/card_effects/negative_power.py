"""Negative power card effects — hindrances queued until their resolve trigger."""

from __future__ import annotations

from typing import TYPE_CHECKING, Callable

from loaded_dice.cards import CardId

if TYPE_CHECKING:
    from loaded_dice.match import Match, Player

# --- Constants (balance here) ---

BLUE_SHELL_POINT_LOSS = 10
POSITIVE_PUNISHMENT_POINT_LOSS = 5
NEGATIVE_PUNISHMENT_CHIP_LOSS = 200

# Resolve on the target's Start Turn (if any condition is met).
START_TURN_HINDRANCES = frozenset(
    {
        CardId.GLASS_HALF_FULL,
        CardId.GLASS_HALF_EMPTY,
        CardId.BLUE_SHELL,
        CardId.POSITIVE_PUNISHMENT,
        CardId.NEGATIVE_PUNISHMENT,
    }
)

# Resolve when the target locks a die (one card per lock).
FIRST_LOCK_HINDRANCES = frozenset({CardId.ALREADY_IN_JAIL})

# --- Hindrance resolvers ---


def _glass_half_full_on_resolve(target: Player, caster: Player, match: Match) -> None:
    target.turn_effects.zero_upper = True


def _glass_half_empty_on_resolve(target: Player, caster: Player, match: Match) -> None:
    target.turn_effects.zero_lower = True


def _blue_shell_on_resolve(target: Player, caster: Player, match: Match) -> None:
    target.lose_points(BLUE_SHELL_POINT_LOSS)


def _already_in_jail_on_resolve(target: Player, caster: Player, match: Match) -> None:
    # Match.lock applies the locked-die restriction when this card is consumed.
    return


def _positive_punishment_on_resolve(target: Player, caster: Player, match: Match) -> None:
    # Armed as pending_score_penalty; applied on the next scored hand.
    target.pending_score_penalty += POSITIVE_PUNISHMENT_POINT_LOSS


def _negative_punishment_on_resolve(target: Player, caster: Player, match: Match) -> None:
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


def punishment_condition_met(target: Player, caster: Player, match: Match) -> bool:
    """Whether positive/negative punishment may resolve this start turn.

    Condition: the target cast a hindrance on anyone during the previous rotation.
    """
    if match.rotation_count == 0:
        return False
    return match.player_attacked_last_rotation(target)


def resolve_hindrance(
    card_id: CardId,
    target: Player,
    caster: Player,
    match: Match,
) -> None:
    """Apply a hindrance effect (caller has already decided it should resolve)."""
    handler = HINDRANCE_RESOLVERS.get(card_id)
    if handler is None:
        raise ValueError(f"No hindrance handler for {card_id.value}")
    handler(target, caster, match)


def try_resolve_hindrance_at_start_turn(
    card_id: CardId,
    target: Player,
    caster: Player,
    match: Match,
) -> bool:
    """Resolve a start-turn hindrance if ready. Returns True if consumed from queue."""
    if card_id in FIRST_LOCK_HINDRANCES:
        return False
    if card_id not in START_TURN_HINDRANCES:
        return False
    if card_id in (CardId.POSITIVE_PUNISHMENT, CardId.NEGATIVE_PUNISHMENT):
        if not punishment_condition_met(target, caster, match):
            return False
    resolve_hindrance(card_id, target, caster, match)
    return True

"""Negative power card effects — hindrances queued until their resolve trigger."""

from __future__ import annotations

from typing import TYPE_CHECKING, Callable

from loaded_dice.cards import CardId
from loaded_dice.turn_brief import BriefAmountLine

if TYPE_CHECKING:
    from loaded_dice.match import Match, Player

# --- Constants (balance here) ---

BLUE_SHELL_POINT_LOSS = 10
POSITIVE_PUNISHMENT_POINT_LOSS = 5
NEGATIVE_PUNISHMENT_CHIP_LOSS = 200
TAX_AUDIT_CHIP_LOSS = 150
BOUNTY_NOTICE_REWARD = 300
SMOKE_BOMB_LOCK_COUNT = 2

# Resolve on the target's Start Turn (if any condition is met).
START_TURN_HINDRANCES = frozenset(
    {
        CardId.GLASS_HALF_FULL,
        CardId.GLASS_HALF_EMPTY,
        CardId.BLUE_SHELL,
        CardId.POSITIVE_PUNISHMENT,
        CardId.NEGATIVE_PUNISHMENT,
        CardId.SMOKE_BOMB,
        CardId.TAX_AUDIT,
    }
)

# Resolve when the target locks a die (one card per lock).
FIRST_LOCK_HINDRANCES = frozenset({CardId.ALREADY_IN_JAIL})

# Stay queued until another hindrance is cast on the marked player (or blocked).
ON_CAST_TRIGGER_HINDRANCES = frozenset({CardId.BOUNTY_NOTICE})

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


def _smoke_bomb_on_resolve(target: Player, caster: Player, match: Match) -> None:
    target.turn_effects.smoke_bomb_locks = SMOKE_BOMB_LOCK_COUNT


def _tax_audit_on_resolve(target: Player, caster: Player, match: Match) -> None:
    before = target.chips
    target.lose_chips(TAX_AUDIT_CHIP_LOSS)
    taken = before - target.chips
    if taken <= 0:
        return
    caster.earn_chips(taken)
    if caster is not match.active_player:
        caster.offturn_chip_events.append(
            BriefAmountLine(taken, f"Tax audit ({target.name})")
        )


HINDRANCE_RESOLVERS: dict[CardId, Callable[[Player, Player, Match], None]] = {
    CardId.GLASS_HALF_FULL: _glass_half_full_on_resolve,
    CardId.GLASS_HALF_EMPTY: _glass_half_empty_on_resolve,
    CardId.POSITIVE_PUNISHMENT: _positive_punishment_on_resolve,
    CardId.NEGATIVE_PUNISHMENT: _negative_punishment_on_resolve,
    CardId.BLUE_SHELL: _blue_shell_on_resolve,
    CardId.ALREADY_IN_JAIL: _already_in_jail_on_resolve,
    CardId.SMOKE_BOMB: _smoke_bomb_on_resolve,
    CardId.TAX_AUDIT: _tax_audit_on_resolve,
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
    if card_id in FIRST_LOCK_HINDRANCES or card_id in ON_CAST_TRIGGER_HINDRANCES:
        return False
    if card_id not in START_TURN_HINDRANCES:
        return False
    if card_id in (CardId.POSITIVE_PUNISHMENT, CardId.NEGATIVE_PUNISHMENT):
        if not punishment_condition_met(target, caster, match):
            return False
    resolve_hindrance(card_id, target, caster, match)
    return True

"""Negative power card effects — hindrances queued until their resolve trigger."""

from __future__ import annotations

from enum import Enum
from typing import TYPE_CHECKING, Callable

from loaded_dice.cards import CardId
from loaded_dice.turn_brief import BriefAmountLine

if TYPE_CHECKING:
    from loaded_dice.match import Match, Player

# --- Constants (balance here) ---

BLUE_SHELL_POINT_LOSS = 10
BLUE_SHELL_CHIP_LOSS = 200
POSITIVE_PUNISHMENT_POINT_LOSS = 5
NEGATIVE_PUNISHMENT_CHIP_LOSS = 200
TAX_AUDIT_CHIP_LOSS = 150
BOUNTY_NOTICE_REWARD = 300
SMOKE_BOMB_LOCK_COUNT = 2
PROVOKE_CHIP_STEAL = 100
PROVOKE_PACIFIST_CHIP_STEAL = 350


class HindranceLinger(Enum):
    """How long a resolved hindrance stays in the debuff fan while it still affects you.

    Rule: if the player is still being affected, keep the card readable in Debuffs.
    New hindrances should pick a linger (default END_OF_TURN if omitted).
    """

    # Fully done at resolve (points/chips already applied) — leave the fan immediately.
    INSTANT = "instant"
    # Still affecting this turn (locks, turn flags, etc.) — clear at end of turn.
    END_OF_TURN = "end_of_turn"
    # Armed across turns until a hand is scored (e.g. pending score penalty).
    UNTIL_SCORE = "until_score"
    # Turn-scoped scoring modifier — clear on score, or at end of turn if unscored.
    UNTIL_SCORE_OR_END_TURN = "until_score_or_end_turn"


# Explicit linger for known cards. Unlisted resolving hindrances default to END_OF_TURN.
HINDRANCE_LINGER: dict[CardId, HindranceLinger] = {
    CardId.BLUE_SHELL: HindranceLinger.INSTANT,
    CardId.TAX_AUDIT: HindranceLinger.INSTANT,
    CardId.PROVOKE: HindranceLinger.INSTANT,
    CardId.NEGATIVE_PUNISHMENT: HindranceLinger.INSTANT,
    CardId.GLASS_HALF_FULL: HindranceLinger.UNTIL_SCORE_OR_END_TURN,
    CardId.GLASS_HALF_EMPTY: HindranceLinger.UNTIL_SCORE_OR_END_TURN,
    CardId.SMOKE_BOMB: HindranceLinger.END_OF_TURN,
    CardId.ALREADY_IN_JAIL: HindranceLinger.END_OF_TURN,
    CardId.POSITIVE_PUNISHMENT: HindranceLinger.UNTIL_SCORE,
}


def hindrance_linger(card_id: CardId) -> HindranceLinger:
    """Linger policy for *card_id* after it resolves (default: end of turn)."""
    return HINDRANCE_LINGER.get(card_id, HindranceLinger.END_OF_TURN)


def persists_after_resolve(card_id: CardId) -> bool:
    return hindrance_linger(card_id) is not HindranceLinger.INSTANT


def clears_active_on_end_turn(card_id: CardId) -> bool:
    return hindrance_linger(card_id) in (
        HindranceLinger.END_OF_TURN,
        HindranceLinger.UNTIL_SCORE_OR_END_TURN,
    )


def clears_active_on_score(card_id: CardId) -> bool:
    return hindrance_linger(card_id) in (
        HindranceLinger.UNTIL_SCORE,
        HindranceLinger.UNTIL_SCORE_OR_END_TURN,
    )


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
        CardId.PROVOKE,
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
    target.lose_chips(BLUE_SHELL_CHIP_LOSS)


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


def provoke_steal_amount(target: Player, match: Match) -> int:
    """100 chips normally; 350 if the target was pacifist last rotation."""
    if match.rotation_count > 0 and match.player_qualifies_as_pacifist(target):
        return PROVOKE_PACIFIST_CHIP_STEAL
    return PROVOKE_CHIP_STEAL


def _provoke_on_resolve(target: Player, caster: Player, match: Match) -> None:
    amount = provoke_steal_amount(target, match)
    before = target.chips
    target.lose_chips(amount)
    taken = before - target.chips
    if taken <= 0:
        return
    caster.earn_chips(taken)
    if caster is not match.active_player:
        caster.offturn_chip_events.append(
            BriefAmountLine(taken, f"Provoke ({target.name})")
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
    CardId.PROVOKE: _provoke_on_resolve,
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

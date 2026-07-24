"""Positive power card effects — cast on self, resolve immediately."""

from __future__ import annotations

from typing import TYPE_CHECKING, Callable

from loaded_dice.cards import Card, CardId, CardKind
from loaded_dice.dice import (
    BENCHWARMER_FACES,
    BOOLEAN_FACES,
    bump_die,
    raise_die_no_wrap,
)
from loaded_dice.scoring import Category

if TYPE_CHECKING:
    from loaded_dice.effects import TurnEffects
    from loaded_dice.match import Match, Player

# --- Constants (balance here) ---

POSITIVE_REINFORCEMENT_BONUS = 8
HELPING_HAND_CHIPS = 400
HELPING_HAND_POINTS = 10
DO_OVER_PLUS_BONUS = 5
DO_OVER_PLUS_CATEGORIES = frozenset(
    {
        Category.FULL_HOUSE,
        Category.FOUR_OF_A_KIND,
        Category.LARGE_STRAIGHT,
        Category.SMALL_STRAIGHT,
    }
)


def compute_do_over_points(
    values: list[int],
    category: Category,
    effects: "TurnEffects | None" = None,
) -> int:
    """Points written by Do over for *values* into *category*.

    For full house / 4oak / straights: only score (base +5) when the hand
    itself qualifies for a non-zero score in that box; otherwise 0.
    """
    from loaded_dice.scoring import apply_turn_modifiers, score_hand

    base = score_hand(values, category)
    if category in DO_OVER_PLUS_CATEGORIES:
        if base == 0:
            return 0
        return apply_turn_modifiers(base, category, effects) + DO_OVER_PLUS_BONUS
    return apply_turn_modifiers(base, category, effects)


# --- Cast handlers ---


def _require_rolled_before_face_change(match: Match) -> None:
    """Face-changing powers are pointless before the first roll of the turn."""
    if match.dice is None or match.dice.rolls_this_turn < 1:
        raise ValueError("Roll at least once before changing dice faces")


def _icarus_on_cast(player: Player, match: Match, **kwargs) -> None:
    die_index = kwargs.get("die_index")
    if die_index is None:
        raise ValueError("Icarus requires die_index")
    _require_rolled_before_face_change(match)
    assert match.dice is not None
    match.ensure_die_mutable(int(die_index))
    try:
        die = match.dice.dice[die_index]
    except IndexError as exc:
        raise ValueError(f"Invalid die index: {die_index}") from exc
    bump_die(die)


def _super_serum_on_cast(player: Player, match: Match, **kwargs) -> None:
    _require_rolled_before_face_change(match)
    assert match.dice is not None
    for index, die in enumerate(match.dice.dice):
        if match.die_is_jailed(index):
            continue
        raise_die_no_wrap(die)


def _do_over_on_cast(player: Player, match: Match, **kwargs) -> None:
    """Overwrite the last scored category with this hand's score in that box.

    Card is already consumed by ``cast_power_card``; validation for Do over
    runs there *before* consume so a blocked second Yahtzee never spends the card.
    """
    die_indices = kwargs.get("die_indices")
    values = match.select_scoring_values_for_effects(die_indices)
    match.apply_do_over(player, values, player.last_scored_category)


def _benchwarmer_on_cast(player: Player, match: Match, **kwargs) -> None:
    if match.dice is None:
        raise ValueError("No dice set for this turn")
    match.dice.add_die(BENCHWARMER_FACES, kind="benchwarmer")


def _helping_hand_on_cast(player: Player, match: Match, **kwargs) -> None:
    choice = kwargs.get("choice")
    target = kwargs.get("target")
    if choice not in ("chips", "points"):
        raise ValueError("Helping hand requires choice='chips' or 'points'")
    if target is None:
        raise ValueError("Helping hand requires target")
    if choice == "chips":
        player.earn_chips(HELPING_HAND_CHIPS)
        target.turn_effects.score_bonus += HELPING_HAND_POINTS
        target.turn_effects.helping_hand_bonus += HELPING_HAND_POINTS
    else:
        player.turn_effects.score_bonus += HELPING_HAND_POINTS
        player.turn_effects.helping_hand_bonus += HELPING_HAND_POINTS
        target.earn_chips(HELPING_HAND_CHIPS)


def _twins_on_cast(player: Player, match: Match, **kwargs) -> None:
    """Link two dice so the follower copies the source on the next roll involving them.

    Does not consume the card — consumption happens when the link resolves on a roll.
    Passing no die_indices while a link is active cancels the link.
    """
    indices = kwargs.get("die_indices")
    if match.dice is None:
        raise ValueError("No dice set for this turn")
    if match.dice.rolls_this_turn < 1:
        raise ValueError("Roll at least once before using Twins")

    # Cancel existing link (card stays in inventory).
    if not indices:
        if not match.dice.twins_links:
            raise ValueError("Twins requires exactly 2 die_indices")
        match.dice.clear_twins()
        return

    if len(indices) != 2:
        raise ValueError("Twins requires exactly 2 die_indices")
    if len(set(indices)) != 2:
        raise ValueError("Twins die indices must be unique")
    leader, follower = int(indices[0]), int(indices[1])
    match.ensure_die_mutable(leader)
    match.ensure_die_mutable(follower)
    try:
        match.dice.queue_twins(leader, follower)
    except (IndexError, ValueError) as exc:
        raise ValueError(str(exc)) from exc


def _space_die_on_cast(player: Player, match: Match, **kwargs) -> None:
    die_index = kwargs.get("die_index")
    face_value = kwargs.get("face_value")
    if die_index is None or face_value is None:
        raise ValueError("Space die requires die_index and face_value")
    _require_rolled_before_face_change(match)
    assert match.dice is not None
    match.ensure_die_mutable(int(die_index))
    try:
        die = match.dice.dice[int(die_index)]
    except IndexError as exc:
        raise ValueError(f"Invalid die index: {die_index}") from exc
    face = int(face_value)
    if face not in die.faces:
        raise ValueError(f"Face {face} not allowed on that die")
    die.value = face


def _boolean_on_cast(player: Player, match: Match, **kwargs) -> None:
    if match.dice is None:
        raise ValueError("No dice set for this turn")
    match.dice.add_die(BOOLEAN_FACES, kind="boolean")


def _write_off_on_cast(player: Player, match: Match, **kwargs) -> None:
    match.end_turn_without_scoring()


def _parry_on_cast(player: Player, match: Match, **kwargs) -> None:
    # Legacy cast path: Prefer UI Use → arm → block_hindrance (consumes from inventory).
    player.parry_ready = True


def try_apply_reinforcements_on_score(player: Player, match: Match) -> None:
    """Consume Positive/Negative Reinforcement when scoring as a pacifist last rotation."""
    if match.rotation_count == 0:
        return
    if match.player_attacked_last_rotation(player):
        return

    if player.inventory.has_power(CardId.POSITIVE_REINFORCEMENT):
        player.turn_effects.score_bonus += POSITIVE_REINFORCEMENT_BONUS
        player.inventory.consume_power_by_id(CardId.POSITIVE_REINFORCEMENT)

    if player.inventory.has_power(CardId.NEGATIVE_REINFORCEMENT):
        player.inventory.consume_power_by_id(CardId.NEGATIVE_REINFORCEMENT)
        player.inventory.add_power(Card(CardId.PARRY, CardKind.POWER, transparent=True))


# Registry: CardId → handler. Handlers receive (player, match, **kwargs).
# Reinforcements are not cast — they auto-apply on score via try_apply_reinforcements_on_score.
POSITIVE_POWER_CAST: dict[CardId, Callable[..., None]] = {
    CardId.ICARUS: _icarus_on_cast,
    CardId.SUPER_SERUM: _super_serum_on_cast,
    CardId.DO_OVER: _do_over_on_cast,
    CardId.BENCHWARMER: _benchwarmer_on_cast,
    CardId.HELPING_HAND: _helping_hand_on_cast,
    CardId.TWINS: _twins_on_cast,
    CardId.SPACE_DIE: _space_die_on_cast,
    CardId.BOOLEAN: _boolean_on_cast,
    CardId.WRITE_OFF: _write_off_on_cast,
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

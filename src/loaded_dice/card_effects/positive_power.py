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
from loaded_dice.scoring import Category, is_yahtzee

if TYPE_CHECKING:
    from loaded_dice.match import Match, Player

# --- Constants (balance here) ---

POSITIVE_REINFORCEMENT_BONUS = 8
HELPING_HAND_CHIPS = 400
HELPING_HAND_POINTS = 10

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
    bump_die(die)


def _super_serum_on_cast(player: Player, match: Match, **kwargs) -> None:
    if match.dice is None:
        raise ValueError("No dice set for this turn")
    for die in match.dice.dice:
        raise_die_no_wrap(die)


def _do_over_on_cast(player: Player, match: Match, **kwargs) -> None:
    """Overwrite the last scored category if current dice match that hand."""
    if player.last_scored_category is None or player.last_scored_values is None:
        raise ValueError("Do over requires a previously scored hand")
    if player.last_scored_category == Category.YAHTZEE:
        raise ValueError("Do over cannot overwrite a Yahtzee")
    if match.dice is None or match.dice.rolls_this_turn < 1:
        raise ValueError("Do over requires rolled dice")

    die_indices = kwargs.get("die_indices")
    values = match.select_scoring_values_for_effects(die_indices)
    if is_yahtzee(values):
        raise ValueError("Do over cannot be used with a Yahtzee hand")
    if sorted(values) != sorted(player.last_scored_values):
        raise ValueError("Current hand must match your last scored hand")

    match.apply_do_over(player, values, player.last_scored_category)


def _benchwarmer_on_cast(player: Player, match: Match, **kwargs) -> None:
    if match.dice is None:
        raise ValueError("No dice set for this turn")
    match.dice.add_die(BENCHWARMER_FACES)


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
    else:
        player.turn_effects.score_bonus += HELPING_HAND_POINTS
        target.earn_chips(HELPING_HAND_CHIPS)


def _twins_on_cast(player: Player, match: Match, **kwargs) -> None:
    indices = kwargs.get("die_indices")
    if indices is None or len(indices) != 2:
        raise ValueError("Twins requires exactly 2 die_indices")
    if len(set(indices)) != 2:
        raise ValueError("Twins die indices must be unique")
    if match.dice is None:
        raise ValueError("No dice set for this turn")
    leader, follower = int(indices[0]), int(indices[1])
    try:
        match.dice.queue_twins(leader, follower)
    except (IndexError, ValueError) as exc:
        raise ValueError(str(exc)) from exc


def _space_die_on_cast(player: Player, match: Match, **kwargs) -> None:
    die_index = kwargs.get("die_index")
    face_value = kwargs.get("face_value")
    if die_index is None or face_value is None:
        raise ValueError("Space die requires die_index and face_value")
    if match.dice is None:
        raise ValueError("No dice set for this turn")
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
    match.dice.add_die(BOOLEAN_FACES)


def _write_off_on_cast(player: Player, match: Match, **kwargs) -> None:
    match.end_turn_without_scoring()


def _parry_on_cast(player: Player, match: Match, **kwargs) -> None:
    # Parry is resolved during TURN_START when the player picks which queued
    # hindrance to block via Match.block_hindrance. Cast marks readiness.
    player.parry_ready = True


def _positive_reinforcement_on_cast(player: Player, match: Match, **kwargs) -> None:
    if match.rotation_count == 0:
        return
    if match.player_attacked_last_rotation(player):
        return
    player.turn_effects.score_bonus += POSITIVE_REINFORCEMENT_BONUS


def _negative_reinforcement_on_cast(player: Player, match: Match, **kwargs) -> None:
    if match.rotation_count == 0:
        return
    if match.player_attacked_last_rotation(player):
        return
    player.inventory.add_power(Card(CardId.PARRY, CardKind.POWER, transparent=True))


# Registry: CardId → handler. Handlers receive (player, match, **kwargs).
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
    CardId.POSITIVE_REINFORCEMENT: _positive_reinforcement_on_cast,
    CardId.NEGATIVE_REINFORCEMENT: _negative_reinforcement_on_cast,
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

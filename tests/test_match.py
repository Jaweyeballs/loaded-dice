import random

import pytest

from loaded_dice.cards import Card, CardId, CardKind
from loaded_dice.dice import TooManyRollsError
from loaded_dice.economy import (
    COMPENSATION_CHIPS_PER_ATTACKER,
    COMPENSATION_PACIFIST_CHIPS,
)
from loaded_dice.match import (
    Match,
    MatchConfig,
    MatchOverError,
    MustRollBeforeScoreError,
    QueuedHindrance,
    TurnPhase,
    WrongPhaseError,
)
from loaded_dice.scoring import Category


def _begin_active_turn(match: Match) -> None:
    match.start_turn()


def _end_turn_quickly(match: Match) -> None:
    if match.phase == TurnPhase.BETWEEN_TURNS:
        _begin_active_turn(match)
    if match.phase == TurnPhase.TURN_START:
        match.begin_rolling()
    if match.phase == TurnPhase.TURN_ACTIVE:
        if match.dice is not None and match.dice.rolls_this_turn < 1:
            match.roll()
        match.end_turn_without_scoring()


def _complete_rotation(match: Match) -> None:
    """Advance until the active player wraps back to whoever started."""
    starting = match.active_player.name
    while True:
        _end_turn_quickly(match)
        if match.active_player.name == starting and match.phase == TurnPhase.BETWEEN_TURNS:
            break


def test_match_requires_at_least_one_player():
    with pytest.raises(ValueError):
        Match([])


def test_start_turn_and_roll():
    match = Match(["Alice", "Bob"])
    _begin_active_turn(match)
    assert match.phase == TurnPhase.TURN_ACTIVE
    assert match.dice is not None
    values = match.roll()
    assert len(values) == 5


def test_cannot_roll_before_start_turn():
    match = Match(["Alice"])
    with pytest.raises(WrongPhaseError):
        match.roll()


def test_cannot_score_before_rolling():
    match = Match(["Alice"])
    _begin_active_turn(match)
    with pytest.raises(MustRollBeforeScoreError):
        match.score(Category.CHANCE)


def test_score_advances_to_next_player():
    match = Match(["Alice", "Bob"])
    _begin_active_turn(match)
    match.roll()
    match.score(Category.CHANCE)
    assert match.phase == TurnPhase.BETWEEN_TURNS
    assert match.active_player.name == "Bob"


def test_end_turn_without_scoring_advances_player():
    match = Match(["Alice", "Bob"])
    _begin_active_turn(match)
    match.roll()
    match.end_turn_without_scoring()
    assert match.active_player.name == "Bob"


def test_lock_and_unlock_during_turn():
    match = Match(["Alice"])
    _begin_active_turn(match)
    match.roll()
    match.lock(0)
    locked = match.dice.dice[0].value
    match.roll()
    assert match.dice.dice[0].value == locked


def test_cannot_lock_before_first_roll():
    match = Match(["Alice"])
    _begin_active_turn(match)
    match.lock(0)
    assert match.dice.dice[0].locked is False


def test_cannot_roll_when_all_dice_locked():
    match = Match(["Alice"])
    _begin_active_turn(match)
    match.roll()
    for i in range(5):
        match.lock(i)
    rolls_before = match.dice.rolls_this_turn
    with pytest.raises(WrongPhaseError, match="locked"):
        match.roll()
    assert match.dice.rolls_this_turn == rolls_before


def test_score_with_extra_dice_uses_best_hand():
    match = Match(["Alice"], config=MatchConfig(dice_size=6))
    _begin_active_turn(match)
    match.roll()
    for i, value in enumerate([1, 2, 3, 4, 5, 6]):
        match.dice.dice[i].value = value
    # Best Chance hand drops the 1 → 2+3+4+5+6 = 20 (client die_indices ignored).
    points = match.score(Category.CHANCE, die_indices=[0, 1, 2, 3, 4])
    assert points == 20


def test_grant_extra_rolls_on_active_turn():
    match = Match(["Alice"])
    _begin_active_turn(match)
    match.roll()
    match.roll()
    match.roll()
    match.grant_extra_rolls(1)
    match.roll()
    with pytest.raises(TooManyRollsError):
        match.roll()


def test_single_sheet_mode_ends_when_all_players_complete():
    random.seed(0)
    match = Match(["Alice", "Bob"])
    categories = list(Category)

    while not match.is_over():
        _begin_active_turn(match)
        match.roll()
        available = [
            c for c in categories if match.active_player.current_sheet.is_available(c)
        ]
        match.score(available[0])

    assert match.winner() is not None
    assert all(player.current_sheet.is_complete() for player in match.players)


def test_max_rotations_mode_ends_early():
    match = Match(["Alice", "Bob"], config=MatchConfig(max_rotations=1))
    _begin_active_turn(match)
    match.roll()
    match.score(Category.CHANCE)
    _begin_active_turn(match)
    match.roll()
    match.score(Category.CHANCE)
    assert match.is_over()
    assert match.rotation_count == 1


def test_refresh_sheet_adds_to_game_total():
    config = MatchConfig(refresh_sheet_on_complete=True, max_rotations=20)
    match = Match(["Alice"], config=config)

    for category in Category:
        _begin_active_turn(match)
        match.roll()
        match.score(category)

    player = match.players[0]
    assert player.sheets_completed == 1
    assert player.game_total > 0
    assert all(player.current_sheet.is_available(c) for c in Category)


def test_cannot_act_after_match_over():
    match = Match(["Alice"], config=MatchConfig(max_rotations=1))
    _begin_active_turn(match)
    match.roll()
    match.score(Category.CHANCE)
    assert match.is_over()
    with pytest.raises(MatchOverError):
        match.start_turn()


def test_cast_icarus_bumps_die_and_consumes_card():
    match = Match(["Alice"])
    match.active_player.inventory.add_power(Card(CardId.ICARUS, CardKind.POWER))
    _begin_active_turn(match)
    match.roll()
    match.dice.dice[2].value = 5
    match.cast_power_card(CardId.ICARUS, die_index=2)
    assert match.dice.dice[2].value == 6
    assert not match.active_player.inventory.has_power(CardId.ICARUS)


def test_cast_icarus_wraps_six_to_one():
    match = Match(["Alice"])
    match.active_player.inventory.add_power(Card(CardId.ICARUS, CardKind.POWER))
    _begin_active_turn(match)
    match.roll()
    match.dice.dice[0].value = 6
    match.cast_power_card(CardId.ICARUS, die_index=0)
    assert match.dice.dice[0].value == 1


def test_cast_power_card_requires_turn_active():
    match = Match(["Alice"])
    match.active_player.inventory.add_power(Card(CardId.ICARUS, CardKind.POWER))
    with pytest.raises(WrongPhaseError):
        match.cast_power_card(CardId.ICARUS, die_index=0)


def test_cast_power_card_requires_card_in_inventory():
    match = Match(["Alice"])
    _begin_active_turn(match)
    match.roll()
    with pytest.raises(WrongPhaseError):
        match.cast_power_card(CardId.ICARUS, die_index=0)


def test_cast_hindrance_queues_on_target_and_consumes_card():
    match = Match(["Alice", "Bob"])
    _begin_active_turn(match)
    alice = match.active_player
    bob = match.players[1]
    alice.inventory.add_power(Card(CardId.GLASS_HALF_FULL, CardKind.POWER))

    match.roll()
    match.cast_hindrance(CardId.GLASS_HALF_FULL, bob)

    assert not alice.inventory.has_power(CardId.GLASS_HALF_FULL)
    assert len(bob.queued_hindrances) == 1
    assert bob.queued_hindrances[0].card_id == CardId.GLASS_HALF_FULL
    assert bob.queued_hindrances[0].caster_name == "Alice"


def test_hindrance_resolves_when_turn_begins():
    match = Match(["Alice", "Bob"])
    _begin_active_turn(match)
    bob = match.players[1]
    match.active_player.inventory.add_power(Card(CardId.GLASS_HALF_FULL, CardKind.POWER))
    match.roll()
    match.cast_hindrance(CardId.GLASS_HALF_FULL, bob)
    match.end_turn_without_scoring()

    assert bob.turn_effects.zero_upper is False
    match.start_turn()
    assert bob.turn_effects.zero_upper is True
    assert bob.queued_hindrances == []


def test_hindrance_affects_scoring_after_start_turn():
    match = Match(["Alice", "Bob"])
    _begin_active_turn(match)
    bob = match.players[1]
    match.active_player.inventory.add_power(Card(CardId.GLASS_HALF_FULL, CardKind.POWER))
    match.roll()
    match.cast_hindrance(CardId.GLASS_HALF_FULL, bob)
    match.end_turn_without_scoring()

    match.start_turn()
    match.roll()
    for die, value in zip(match.dice.dice, [3, 3, 3, 1, 2]):
        die.value = value
    points = match.score(Category.THREES)
    assert points == 0


def test_block_hindrance_cancels_one_queued_effect():
    match = Match(["Alice", "Bob"])
    _begin_active_turn(match)
    match.end_turn_without_scoring()
    bob = match.active_player
    assert bob.name == "Bob"
    bob.queued_hindrances.extend(
        [
            QueuedHindrance(card_id=CardId.GLASS_HALF_FULL, caster_name="Alice"),
            QueuedHindrance(card_id=CardId.GLASS_HALF_EMPTY, caster_name="Alice"),
        ]
    )
    bob.inventory.add_power(Card(CardId.PARRY, CardKind.POWER))

    match.block_hindrance(0)
    match.start_turn()
    assert bob.turn_effects.zero_upper is False
    assert bob.turn_effects.zero_lower is True


def test_block_hindrance_can_use_parry_ready():
    match = Match(["Alice", "Bob"])
    _begin_active_turn(match)
    bob = match.players[1]
    match.active_player.inventory.add_power(Card(CardId.GLASS_HALF_FULL, CardKind.POWER))
    match.roll()
    match.cast_hindrance(CardId.GLASS_HALF_FULL, bob)
    match.end_turn_without_scoring()

    assert match.active_player.name == "Bob"
    bob.parry_ready = True
    match.block_hindrance(0)
    match.start_turn()
    assert bob.turn_effects.zero_upper is False
    assert bob.parry_ready is False


def test_block_hindrance_before_own_turn_while_others_play():
    match = Match(["Alice", "Bob"])
    _begin_active_turn(match)
    bob = match.players[1]
    bob.queued_hindrances.append(
        QueuedHindrance(card_id=CardId.GLASS_HALF_FULL, caster_name="Alice")
    )
    bob.inventory.add_power(Card(CardId.PARRY, CardKind.POWER))
    # Alice is still mid-turn; Bob blocks his own queued hindrance.
    match.block_hindrance(0, player=bob)
    assert bob.queued_hindrances == []
    assert not bob.inventory.has_power(CardId.PARRY)

def test_cannot_queue_conflicting_glass_half_hindrances():
    match = Match(["Alice", "Bob"])
    _begin_active_turn(match)
    bob = match.players[1]
    match.active_player.inventory.add_power(Card(CardId.GLASS_HALF_FULL, CardKind.POWER))
    match.active_player.inventory.add_power(Card(CardId.GLASS_HALF_EMPTY, CardKind.POWER))
    match.roll()
    match.cast_hindrance(CardId.GLASS_HALF_FULL, bob)
    with pytest.raises(WrongPhaseError):
        match.cast_hindrance(CardId.GLASS_HALF_EMPTY, bob)


def test_cannot_cast_hindrance_on_self():
    match = Match(["Alice", "Bob"])
    _begin_active_turn(match)
    match.active_player.inventory.add_power(Card(CardId.GLASS_HALF_FULL, CardKind.POWER))
    match.roll()
    with pytest.raises(ValueError):
        match.cast_hindrance(CardId.GLASS_HALF_FULL, match.active_player)


def test_cast_hindrance_requires_turn_active():
    match = Match(["Alice", "Bob"])
    match.active_player.inventory.add_power(Card(CardId.GLASS_HALF_FULL, CardKind.POWER))
    with pytest.raises(WrongPhaseError):
        match.cast_hindrance(CardId.GLASS_HALF_FULL, match.players[1])


def test_no_compensation_on_first_rotation():
    match = Match(["Alice", "Bob"])
    match.start_turn()
    assert match.players[0].chips == 0


def test_compensation_pacifist_bonus_after_rotation():
    match = Match(["Alice", "Bob"])
    _complete_rotation(match)
    match.start_turn()
    assert match.active_player.chips == COMPENSATION_PACIFIST_CHIPS


def test_compensation_pays_for_being_attacked_last_rotation():
    match = Match(["Alice", "Bob", "Carol"])
    _begin_active_turn(match)
    alice = match.active_player
    bob = match.players[1]
    alice.inventory.add_power(Card(CardId.GLASS_HALF_FULL, CardKind.POWER))
    match.roll()
    match.cast_hindrance(CardId.GLASS_HALF_FULL, bob)
    _complete_rotation(match)

    while match.active_player.name != "Bob":
        _end_turn_quickly(match)
    match.start_turn()
    assert bob.chips == COMPENSATION_PACIFIST_CHIPS + COMPENSATION_CHIPS_PER_ATTACKER


def test_compensation_no_pacifist_bonus_if_player_attacked():
    match = Match(["Alice", "Bob"])
    _begin_active_turn(match)
    match.active_player.inventory.add_power(Card(CardId.GLASS_HALF_FULL, CardKind.POWER))
    match.roll()
    match.cast_hindrance(CardId.GLASS_HALF_FULL, match.players[1])
    _complete_rotation(match)

    match.start_turn()
    assert match.active_player.chips == 0


def test_compensation_counts_unique_attackers_only_once():
    match = Match(["Alice", "Bob", "Carol"])
    bob = match.players[1]
    _begin_active_turn(match)
    match.active_player.inventory.add_power(Card(CardId.GLASS_HALF_FULL, CardKind.POWER))
    match.roll()
    match.cast_hindrance(CardId.GLASS_HALF_FULL, bob)
    _end_turn_quickly(match)
    _end_turn_quickly(match)
    _begin_active_turn(match)
    assert match.active_player.name == "Carol"
    match.active_player.inventory.add_power(Card(CardId.GLASS_HALF_EMPTY, CardKind.POWER))
    match.roll()
    match.cast_hindrance(CardId.GLASS_HALF_EMPTY, bob)
    _end_turn_quickly(match)
    _end_turn_quickly(match)

    match.start_turn()
    assert bob.chips == COMPENSATION_PACIFIST_CHIPS + 2 * COMPENSATION_CHIPS_PER_ATTACKER


def test_player_attacked_last_rotation_tracks_hindrance_casts():
    match = Match(["Alice", "Bob"])
    _begin_active_turn(match)
    match.active_player.inventory.add_power(Card(CardId.GLASS_HALF_FULL, CardKind.POWER))
    match.roll()
    match.cast_hindrance(CardId.GLASS_HALF_FULL, match.players[1])
    _complete_rotation(match)

    assert match.player_attacked_last_rotation(match.players[0]) is True
    assert match.player_attacked_last_rotation(match.players[1]) is False
    assert match.attackers_on_player_last_rotation(match.players[1]) == frozenset({"Alice"})

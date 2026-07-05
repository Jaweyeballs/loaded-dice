import random

import pytest

from loaded_dice.cards import Card, CardId, CardKind
from loaded_dice.dice import TooManyRollsError
from loaded_dice.match import (
    InvalidDieSelectionError,
    Match,
    MatchConfig,
    MatchOverError,
    MustRollBeforeScoreError,
    TurnPhase,
    WrongPhaseError,
)
from loaded_dice.scoring import Category


def _begin_active_turn(match: Match) -> None:
    match.start_turn()
    match.begin_rolling()


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


def test_cannot_roll_before_begin_rolling():
    match = Match(["Alice"])
    match.start_turn()
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


def test_score_with_selected_dice_when_more_than_five():
    match = Match(["Alice"], config=MatchConfig(dice_size=6))
    _begin_active_turn(match)
    match.roll()
    # Force values so we can verify index selection matters
    for i, value in enumerate([1, 2, 3, 4, 5, 6]):
        match.dice.dice[i].value = value
    points = match.score(Category.CHANCE, die_indices=[0, 1, 2, 3, 4])
    assert points == 15


def test_score_requires_die_selection_when_more_than_five():
    match = Match(["Alice"], config=MatchConfig(dice_size=6))
    _begin_active_turn(match)
    match.roll()
    with pytest.raises(InvalidDieSelectionError):
        match.score(Category.CHANCE)


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
    match.start_turn()
    with pytest.raises(WrongPhaseError):
        match.cast_power_card(CardId.ICARUS, die_index=0)


def test_cast_power_card_requires_card_in_inventory():
    match = Match(["Alice"])
    _begin_active_turn(match)
    match.roll()
    with pytest.raises(WrongPhaseError):
        match.cast_power_card(CardId.ICARUS, die_index=0)

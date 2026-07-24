"""Tests for newly implemented GDD power cards."""

import pytest

from loaded_dice.actions import apply_action
from loaded_dice.cards import CardId, card_for_id
from loaded_dice.match import Match, WrongPhaseError
from loaded_dice.scoring import Category


def _begin_active_turn(match: Match) -> None:
    match.start_turn()


def test_super_serum_bumps_all_dice():
    match = Match(["Alice"])
    match.players[0].inventory.add_power(card_for_id(CardId.SUPER_SERUM))
    _begin_active_turn(match)
    match.roll()
    assert match.dice is not None
    for i, face in enumerate([1, 3, 6, 5, 2]):
        match.dice.dice[i].value = face
    match.cast_power_card(CardId.SUPER_SERUM)
    assert match.dice.values == [2, 4, 6, 6, 3]


def test_space_die_sets_face():
    match = Match(["Alice"])
    match.players[0].inventory.add_power(card_for_id(CardId.SPACE_DIE))
    _begin_active_turn(match)
    match.roll()
    match.cast_power_card(CardId.SPACE_DIE, die_index=0, face_value=6)
    assert match.dice is not None
    assert match.dice.values[0] == 6


def test_write_off_ends_turn():
    match = Match(["Alice", "Bob"])
    match.players[0].inventory.add_power(card_for_id(CardId.WRITE_OFF))
    _begin_active_turn(match)
    match.roll()
    match.cast_power_card(CardId.WRITE_OFF)
    assert match.active_player.name == "Bob"


def test_benchwarmer_adds_die():
    match = Match(["Alice"])
    match.players[0].inventory.add_power(card_for_id(CardId.BENCHWARMER))
    _begin_active_turn(match)
    match.roll()
    match.cast_power_card(CardId.BENCHWARMER)
    assert match.dice is not None
    assert len(match.dice.dice) == 6


def test_boolean_adds_special_die():
    match = Match(["Alice"])
    match.players[0].inventory.add_power(card_for_id(CardId.BOOLEAN))
    _begin_active_turn(match)
    match.roll()
    match.cast_power_card(CardId.BOOLEAN)
    assert match.dice is not None
    assert len(match.dice.dice) == 6
    assert set(match.dice.dice[-1].faces) == {0, 6}


def test_helping_hand_chips_choice():
    match = Match(["Alice", "Bob"])
    alice, bob = match.players
    alice.inventory.add_power(card_for_id(CardId.HELPING_HAND))
    _begin_active_turn(match)
    match.roll()
    before = alice.chips
    match.cast_power_card(CardId.HELPING_HAND, choice="chips", target=bob)
    assert alice.chips == before + 400
    assert bob.turn_effects.score_bonus == 10
    assert bob.turn_effects.helping_hand_bonus == 10


def test_twins_links_for_next_roll_and_consumes_on_roll():
    match = Match(["Alice"])
    alice = match.players[0]
    alice.inventory.add_power(card_for_id(CardId.TWINS))
    _begin_active_turn(match)
    match.roll()
    assert match.dice is not None
    for i, face in enumerate([1, 2, 3, 4, 5]):
        match.dice.dice[i].value = face
    match.cast_power_card(CardId.TWINS, die_indices=[0, 1])
    assert alice.inventory.has_power(CardId.TWINS)
    assert match.dice.twins_links == {1: 0}

    for i in range(5):
        match.unlock(i)
    match.dice.queue_forced_roll(0, 5)
    match.roll()
    assert match.dice.values[0] == 5
    assert match.dice.values[1] == 5
    assert match.dice.twins_links == {}
    assert not alice.inventory.has_power(CardId.TWINS)


def test_twins_cancel_clears_link_without_consuming():
    match = Match(["Alice"])
    alice = match.players[0]
    alice.inventory.add_power(card_for_id(CardId.TWINS))
    _begin_active_turn(match)
    match.roll()
    match.cast_power_card(CardId.TWINS, die_indices=[2, 4])
    assert match.dice is not None
    assert match.dice.twins_links == {4: 2}
    match.cast_power_card(CardId.TWINS)  # cancel
    assert match.dice.twins_links == {}
    assert alice.inventory.has_power(CardId.TWINS)


def test_twins_score_without_rolling_keeps_card():
    match = Match(["Alice"])
    alice = match.players[0]
    alice.inventory.add_power(card_for_id(CardId.TWINS))
    _begin_active_turn(match)
    match.roll()
    assert match.dice is not None
    for i, face in enumerate([1, 2, 3, 4, 5]):
        match.dice.dice[i].value = face
    match.cast_power_card(CardId.TWINS, die_indices=[0, 1])
    match.score(Category.CHANCE)
    assert alice.inventory.has_power(CardId.TWINS)


def test_twins_mirrors_psychic_ghost_from_source():
    match = Match(["Alice"])
    alice = match.players[0]
    alice.inventory.add_power(card_for_id(CardId.TWINS))
    alice.inventory.add_trading(card_for_id(CardId.PSYCHIC))
    _begin_active_turn(match)
    match.roll()
    match.activate_trading_card(CardId.PSYCHIC, die_indices=[0, 3])
    source_preview = match.psychic_previews[0]
    assert 1 not in match.psychic_previews
    match.cast_power_card(CardId.TWINS, die_indices=[0, 1])
    assert match.psychic_previews[1] == source_preview
    match.cast_power_card(CardId.TWINS)  # cancel
    assert 1 not in match.psychic_previews
    assert match.psychic_previews[0] == source_preview


def test_toddler_on_twins_link_consumes_card():
    match = Match(["Alice"])
    alice = match.players[0]
    alice.inventory.add_power(card_for_id(CardId.TWINS))
    alice.inventory.add_trading(card_for_id(CardId.TODDLER))
    _begin_active_turn(match)
    match.roll()
    assert match.dice is not None
    match.cast_power_card(CardId.TWINS, die_indices=[0, 1])
    match.activate_trading_card(CardId.TODDLER, die_indices=[0, 1])
    assert match.dice.values[0] == match.dice.values[1]
    assert match.dice.twins_links == {}
    assert not alice.inventory.has_power(CardId.TWINS)


def test_do_over_overwrites_last_category_without_matching_hand():
    match = Match(["Alice"])
    alice = match.players[0]
    alice.inventory.add_power(card_for_id(CardId.DO_OVER))
    _begin_active_turn(match)
    match.roll()
    assert match.dice is not None
    for i, face in enumerate([1, 2, 3, 4, 5]):
        match.dice.dice[i].value = face
    match.score(Category.CHANCE)
    assert alice.last_scored_category == Category.CHANCE
    assert alice.current_sheet.get_score(Category.CHANCE) == 15

    _begin_active_turn(match)
    match.roll()
    # Different faces — Do over still overwrites Chance with this hand's Chance score.
    for i, face in enumerate([6, 6, 6, 1, 2]):
        match.dice.dice[i].value = face
    match.do_over()
    assert alice.current_sheet.get_score(Category.CHANCE) == 21
    assert not alice.inventory.has_power(CardId.DO_OVER)


def test_do_over_plus_five_on_full_house_category():
    match = Match(["Alice"])
    alice = match.players[0]
    alice.inventory.add_power(card_for_id(CardId.DO_OVER))
    _begin_active_turn(match)
    match.roll()
    assert match.dice is not None
    for i, face in enumerate([2, 2, 3, 3, 3]):
        match.dice.dice[i].value = face
    match.score(Category.FULL_HOUSE)
    assert alice.current_sheet.get_score(Category.FULL_HOUSE) == 25

    _begin_active_turn(match)
    match.roll()
    for i, face in enumerate([5, 5, 6, 6, 6]):
        match.dice.dice[i].value = face
    match.do_over()
    # Full house base 25 + Do over +5
    assert alice.current_sheet.get_score(Category.FULL_HOUSE) == 30


def test_do_over_poker_box_zero_when_hand_does_not_qualify():
    match = Match(["Alice"])
    alice = match.players[0]
    alice.inventory.add_power(card_for_id(CardId.DO_OVER))
    _begin_active_turn(match)
    match.roll()
    assert match.dice is not None
    for i, face in enumerate([1, 2, 3, 4, 6]):
        match.dice.dice[i].value = face
    match.score(Category.SMALL_STRAIGHT)
    assert alice.current_sheet.get_score(Category.SMALL_STRAIGHT) == 30

    _begin_active_turn(match)
    match.roll()
    for i, face in enumerate([1, 1, 3, 5, 6]):
        match.dice.dice[i].value = face
    match.do_over()
    assert alice.current_sheet.get_score(Category.SMALL_STRAIGHT) == 0


def test_do_over_small_straight_qualifying_hand_scores_thirty_five():
    match = Match(["Alice"])
    alice = match.players[0]
    alice.inventory.add_power(card_for_id(CardId.DO_OVER))
    _begin_active_turn(match)
    match.roll()
    assert match.dice is not None
    for i, face in enumerate([1, 2, 3, 4, 6]):
        match.dice.dice[i].value = face
    match.score(Category.SMALL_STRAIGHT)

    _begin_active_turn(match)
    match.roll()
    for i, face in enumerate([2, 3, 4, 5, 5]):
        match.dice.dice[i].value = face
    match.do_over()
    assert alice.current_sheet.get_score(Category.SMALL_STRAIGHT) == 35


def test_do_over_blocked_when_overwriting_yahtzee():
    match = Match(["Alice"])
    alice = match.players[0]
    alice.inventory.add_power(card_for_id(CardId.DO_OVER))
    _begin_active_turn(match)
    match.roll()
    assert match.dice is not None
    for i, face in enumerate([4, 4, 4, 4, 4]):
        match.dice.dice[i].value = face
    match.score(Category.YAHTZEE)

    _begin_active_turn(match)
    match.roll()
    for i, face in enumerate([1, 2, 3, 4, 5]):
        match.dice.dice[i].value = face
    with pytest.raises(ValueError, match="cannot overwrite a Yahtzee"):
        match.do_over()
    assert alice.inventory.has_power(CardId.DO_OVER)


def test_do_over_does_not_consume_on_second_yahtzee():
    match = Match(["Alice"])
    alice = match.players[0]
    alice.inventory.add_power(card_for_id(CardId.DO_OVER))
    _begin_active_turn(match)
    match.roll()
    assert match.dice is not None
    for i, face in enumerate([5, 5, 5, 5, 5]):
        match.dice.dice[i].value = face
    match.score(Category.YAHTZEE)

    _begin_active_turn(match)
    match.roll()
    for i, face in enumerate([1, 2, 3, 4, 6]):
        match.dice.dice[i].value = face
    match.score(Category.CHANCE)
    assert alice.last_scored_category == Category.CHANCE

    _begin_active_turn(match)
    match.roll()
    for i, face in enumerate([3, 3, 3, 3, 3]):
        match.dice.dice[i].value = face
    with pytest.raises(ValueError, match="another Yahtzee"):
        match.do_over()
    assert alice.inventory.has_power(CardId.DO_OVER)
    assert alice.current_sheet.get_score(Category.CHANCE) == 16


def test_blue_shell_queues_on_leader():
    match = Match(["Alice", "Bob"])
    alice, bob = match.players
    bob.game_total = 50
    alice.inventory.add_power(card_for_id(CardId.BLUE_SHELL))
    _begin_active_turn(match)
    match.roll()
    match.cast_hindrance(CardId.BLUE_SHELL)
    assert bob.queued_hindrances[0].card_id == CardId.BLUE_SHELL
    match.end_turn_without_scoring()
    match.start_turn()
    match.begin_rolling()
    assert bob.game_total == 40


def test_already_in_jail_locks_first_die():
    match = Match(["Alice", "Bob"])
    alice, bob = match.players
    alice.inventory.add_power(card_for_id(CardId.ALREADY_IN_JAIL))
    _begin_active_turn(match)
    match.roll()
    match.cast_hindrance(CardId.ALREADY_IN_JAIL, bob)
    match.end_turn_without_scoring()
    match.start_turn()
    assert len(bob.queued_hindrances) == 1
    assert bob.queued_hindrances[0].card_id == CardId.ALREADY_IN_JAIL
    match.roll()
    match.lock(2)
    assert bob.queued_hindrances == []
    assert bob.jail_locked_index == 2
    with pytest.raises(WrongPhaseError, match="jail"):
        match.unlock(2)


def test_already_in_jail_can_be_blocked_after_start_turn():
    match = Match(["Alice", "Bob"])
    alice, bob = match.players
    alice.inventory.add_power(card_for_id(CardId.ALREADY_IN_JAIL))
    bob.inventory.add_power(card_for_id(CardId.PARRY))
    _begin_active_turn(match)
    match.roll()
    match.cast_hindrance(CardId.ALREADY_IN_JAIL, bob)
    match.end_turn_without_scoring()
    match.start_turn()
    assert len(bob.queued_hindrances) == 1
    match.block_hindrance(0)
    assert bob.queued_hindrances == []
    match.roll()
    match.lock(0)
    assert bob.jail_locked_index is None
    match.unlock(0)


def test_already_in_jail_stacks_one_per_lock():
    match = Match(["Alice", "Bob"])
    alice, bob = match.players
    alice.inventory.add_power(card_for_id(CardId.ALREADY_IN_JAIL))
    alice.inventory.add_power(card_for_id(CardId.ALREADY_IN_JAIL))
    _begin_active_turn(match)
    match.roll()
    match.cast_hindrance(CardId.ALREADY_IN_JAIL, bob)
    match.cast_hindrance(CardId.ALREADY_IN_JAIL, bob)
    match.end_turn_without_scoring()
    match.start_turn()
    assert len(bob.queued_hindrances) == 2
    match.roll()
    match.lock(1)
    assert bob.jail_locked_index == 1
    assert len(bob.queued_hindrances) == 1
    with pytest.raises(WrongPhaseError, match="jail"):
        match.unlock(1)


def test_already_in_jail_blocks_face_changing_effects():
    match = Match(["Alice", "Bob"])
    alice, bob = match.players
    alice.inventory.add_power(card_for_id(CardId.ALREADY_IN_JAIL))
    _begin_active_turn(match)
    match.roll()
    match.cast_hindrance(CardId.ALREADY_IN_JAIL, bob)
    match.end_turn_without_scoring()
    match.start_turn()
    match.roll()
    match.lock(2)
    assert bob.jail_locked_index == 2
    face = match.dice.dice[2].value

    bob.inventory.add_power(card_for_id(CardId.ICARUS))
    with pytest.raises(WrongPhaseError, match="jail"):
        match.cast_power_card(CardId.ICARUS, die_index=2)
    assert match.dice.dice[2].value == face

    bob.inventory.add_power(card_for_id(CardId.SPACE_DIE))
    with pytest.raises(WrongPhaseError, match="jail"):
        match.cast_power_card(CardId.SPACE_DIE, die_index=2, face_value=6)
    assert match.dice.dice[2].value == face

    bob.inventory.add_power(card_for_id(CardId.SUPER_SERUM))
    match.cast_power_card(CardId.SUPER_SERUM)
    assert match.dice.dice[2].value == face

    bob.inventory.add_trading(card_for_id(CardId.TODDLER))
    with pytest.raises(WrongPhaseError, match="jail"):
        match.activate_trading_card(CardId.TODDLER, die_indices=[2, 0])
    assert match.dice.dice[2].value == face

    bob.inventory.add_trading(card_for_id(CardId.PSYCHIC))
    with pytest.raises(WrongPhaseError, match="jail"):
        match.activate_trading_card(CardId.PSYCHIC, die_indices=[2, 0])
    assert match.dice.dice[2].value == face


def test_already_in_jail_persists_if_turn_ends_without_lock():
    match = Match(["Alice", "Bob"])
    alice, bob = match.players
    alice.inventory.add_power(card_for_id(CardId.ALREADY_IN_JAIL))
    _begin_active_turn(match)
    match.roll()
    match.cast_hindrance(CardId.ALREADY_IN_JAIL, bob)
    match.end_turn_without_scoring()
    match.start_turn()
    match.roll()
    match.end_turn_without_scoring()
    assert len(bob.queued_hindrances) == 1
    assert bob.queued_hindrances[0].card_id == CardId.ALREADY_IN_JAIL


def test_score_with_extra_die_requires_selection():
    match = Match(["Alice"])
    match.players[0].inventory.add_power(card_for_id(CardId.BENCHWARMER))
    _begin_active_turn(match)
    match.roll()
    match.cast_power_card(CardId.BENCHWARMER)
    with pytest.raises(Exception):
        match.score(Category.CHANCE)
    match.score(Category.CHANCE, die_indices=[0, 1, 2, 3, 4])

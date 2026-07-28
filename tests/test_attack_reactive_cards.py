import pytest

from loaded_dice.card_effects.negative_power import (
    NEGATIVE_PUNISHMENT_CHIP_LOSS,
    POSITIVE_PUNISHMENT_POINT_LOSS,
)
from loaded_dice.card_effects.positive_power import POSITIVE_REINFORCEMENT_BONUS
from loaded_dice.cards import Card, CardId, CardKind
from loaded_dice.match import Match, TurnPhase
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
    starting = match.active_player.name
    while True:
        _end_turn_quickly(match)
        if match.active_player.name == starting and match.phase == TurnPhase.BETWEEN_TURNS:
            break


def test_positive_reinforcement_bonus_when_pacifist_last_rotation():
    match = Match(["Alice", "Bob"])
    _complete_rotation(match)
    alice = match.active_player
    assert alice.name == "Alice"
    alice.inventory.add_power(Card(CardId.POSITIVE_REINFORCEMENT, CardKind.POWER))
    _begin_active_turn(match)
    match.roll()
    for die, value in zip(match.dice.dice, [3, 3, 3, 1, 2]):
        die.value = value
    points = match.score(Category.THREES)
    assert points == 9 + POSITIVE_REINFORCEMENT_BONUS
    assert not alice.inventory.has_power(CardId.POSITIVE_REINFORCEMENT)


def test_positive_reinforcement_no_bonus_if_attacked_last_rotation():
    match = Match(["Alice", "Bob"])
    _begin_active_turn(match)
    match.active_player.inventory.add_power(Card(CardId.GLASS_HALF_FULL, CardKind.POWER))
    match.roll()
    match.cast_hindrance(CardId.GLASS_HALF_FULL, match.players[1])
    _complete_rotation(match)

    alice = match.active_player
    alice.inventory.add_power(Card(CardId.POSITIVE_REINFORCEMENT, CardKind.POWER))
    _begin_active_turn(match)
    match.roll()
    for die, value in zip(match.dice.dice, [3, 3, 3, 1, 2]):
        die.value = value
    points = match.score(Category.THREES)
    assert points == 9
    assert alice.inventory.has_power(CardId.POSITIVE_REINFORCEMENT)


def test_positive_reinforcement_kept_on_write_off():
    match = Match(["Alice", "Bob"])
    _complete_rotation(match)
    alice = match.active_player
    alice.inventory.add_power(Card(CardId.POSITIVE_REINFORCEMENT, CardKind.POWER))
    _begin_active_turn(match)
    match.roll()
    match.end_turn_without_scoring()
    assert alice.inventory.has_power(CardId.POSITIVE_REINFORCEMENT)


def test_negative_reinforcement_grants_transparent_parry():
    match = Match(["Alice", "Bob"])
    _complete_rotation(match)
    match.active_player.inventory.add_power(
        Card(CardId.NEGATIVE_REINFORCEMENT, CardKind.POWER)
    )
    _begin_active_turn(match)
    match.roll()
    for die, value in zip(match.dice.dice, [3, 3, 3, 1, 2]):
        die.value = value
    match.score(Category.THREES)
    parry_cards = [
        card
        for card in match.players[0].inventory.power_cards
        if card.id == CardId.PARRY
    ]
    assert len(parry_cards) == 1
    assert parry_cards[0].transparent is True
    assert match.players[0].inventory.power_slots_used() == 0
    assert not match.players[0].inventory.has_power(CardId.NEGATIVE_REINFORCEMENT)


def test_positive_punishment_penalizes_scoring_when_target_attacked_anyone():
    match = Match(["Alice", "Bob"])
    alice = match.players[0]
    bob = match.players[1]
    _begin_active_turn(match)
    _end_turn_quickly(match)
    assert match.active_player.name == "Bob"
    _begin_active_turn(match)
    bob.inventory.add_power(Card(CardId.GLASS_HALF_FULL, CardKind.POWER))
    match.roll()
    match.cast_hindrance(CardId.GLASS_HALF_FULL, alice)
    _end_turn_quickly(match)
    assert match.rotation_count == 1
    assert match.active_player.name == "Alice"

    alice.inventory.add_power(Card(CardId.POSITIVE_PUNISHMENT, CardKind.POWER))
    _begin_active_turn(match)
    match.roll()
    match.cast_hindrance(CardId.POSITIVE_PUNISHMENT, bob)
    _end_turn_quickly(match)

    match.start_turn()
    match.begin_rolling()
    match.roll()
    for die, value in zip(match.dice.dice, [3, 3, 3, 1, 2]):
        die.value = value
    points = match.score(Category.THREES)
    assert points == 9 - POSITIVE_PUNISHMENT_POINT_LOSS


def test_positive_punishment_applies_when_target_attacked_someone_else():
    match = Match(["Alice", "Bob", "Carol"])
    alice, bob, carol = match.players
    _begin_active_turn(match)
    _end_turn_quickly(match)
    _begin_active_turn(match)  # Bob
    bob.inventory.add_power(Card(CardId.GLASS_HALF_FULL, CardKind.POWER))
    match.roll()
    match.cast_hindrance(CardId.GLASS_HALF_FULL, carol)  # Bob attacks Carol, not Alice
    _end_turn_quickly(match)
    _end_turn_quickly(match)  # Carol
    assert match.rotation_count == 1
    assert match.active_player.name == "Alice"

    alice.inventory.add_power(Card(CardId.POSITIVE_PUNISHMENT, CardKind.POWER))
    _begin_active_turn(match)
    match.roll()
    match.cast_hindrance(CardId.POSITIVE_PUNISHMENT, bob)
    _end_turn_quickly(match)

    match.start_turn()  # Bob
    assert bob.pending_score_penalty == POSITIVE_PUNISHMENT_POINT_LOSS
    match.roll()
    for die, value in zip(match.dice.dice, [3, 3, 3, 1, 2]):
        die.value = value
    points = match.score(Category.THREES)
    assert points == 9 - POSITIVE_PUNISHMENT_POINT_LOSS


def test_positive_punishment_no_effect_if_target_did_not_attack_anyone():
    match = Match(["Alice", "Bob"])
    _complete_rotation(match)
    alice = match.active_player
    bob = match.players[1]
    alice.inventory.add_power(Card(CardId.POSITIVE_PUNISHMENT, CardKind.POWER))
    _begin_active_turn(match)
    match.roll()
    match.cast_hindrance(CardId.POSITIVE_PUNISHMENT, bob)
    _end_turn_quickly(match)

    match.start_turn()
    match.begin_rolling()
    match.roll()
    for die, value in zip(match.dice.dice, [3, 3, 3, 1, 2]):
        die.value = value
    points = match.score(Category.THREES)
    assert points == 9
    assert len(bob.queued_hindrances) == 1
    assert bob.queued_hindrances[0].card_id == CardId.POSITIVE_PUNISHMENT


def test_positive_punishment_survives_write_off_until_score():
    match = Match(["Alice", "Bob"])
    alice = match.players[0]
    bob = match.players[1]
    _begin_active_turn(match)
    _end_turn_quickly(match)
    _begin_active_turn(match)
    bob.inventory.add_power(Card(CardId.GLASS_HALF_FULL, CardKind.POWER))
    match.roll()
    match.cast_hindrance(CardId.GLASS_HALF_FULL, alice)
    _end_turn_quickly(match)

    alice.inventory.add_power(Card(CardId.POSITIVE_PUNISHMENT, CardKind.POWER))
    _begin_active_turn(match)
    match.roll()
    match.cast_hindrance(CardId.POSITIVE_PUNISHMENT, bob)
    _end_turn_quickly(match)

    match.start_turn()
    assert bob.pending_score_penalty == POSITIVE_PUNISHMENT_POINT_LOSS
    assert len(bob.queued_hindrances) == 1
    assert bob.queued_hindrances[0].card_id == CardId.POSITIVE_PUNISHMENT
    assert bob.queued_hindrances[0].active is True
    match.end_turn_without_scoring()

    _end_turn_quickly(match)  # Alice
    match.start_turn()  # Bob again
    assert bob.pending_score_penalty == POSITIVE_PUNISHMENT_POINT_LOSS
    assert bob.queued_hindrances[0].active is True
    match.roll()
    for die, value in zip(match.dice.dice, [3, 3, 3, 1, 2]):
        die.value = value
    points = match.score(Category.THREES)
    assert points == 9 - POSITIVE_PUNISHMENT_POINT_LOSS
    assert bob.pending_score_penalty == 0
    assert bob.queued_hindrances == []


def test_negative_punishment_waits_when_condition_not_met():
    match = Match(["Alice", "Bob"])
    _complete_rotation(match)
    alice = match.active_player
    bob = match.players[1]
    bob.chips = 500
    alice.inventory.add_power(Card(CardId.NEGATIVE_PUNISHMENT, CardKind.POWER))
    _begin_active_turn(match)
    match.roll()
    match.cast_hindrance(CardId.NEGATIVE_PUNISHMENT, bob)
    _end_turn_quickly(match)

    from loaded_dice.economy import calculate_compensation, calculate_interest

    chips_before = bob.chips
    interest = calculate_interest(chips_before)
    compensation = calculate_compensation(
        match._previous_rotation_attacks.attacker_count_on(bob.name),
        match._previous_rotation_attacks.player_attacked(bob.name),
    )
    match.start_turn()
    assert bob.queued_hindrances[0].card_id == CardId.NEGATIVE_PUNISHMENT
    assert bob.chips == chips_before + interest + compensation


def test_negative_punishment_deducts_chips_when_target_attacked_caster():
    match = Match(["Alice", "Bob"])
    alice = match.players[0]
    bob = match.players[1]
    bob.chips = 500
    _begin_active_turn(match)
    _end_turn_quickly(match)
    _begin_active_turn(match)
    bob.inventory.add_power(Card(CardId.GLASS_HALF_FULL, CardKind.POWER))
    match.roll()
    match.cast_hindrance(CardId.GLASS_HALF_FULL, alice)
    _end_turn_quickly(match)

    alice.inventory.add_power(Card(CardId.NEGATIVE_PUNISHMENT, CardKind.POWER))
    _begin_active_turn(match)
    match.roll()
    match.cast_hindrance(CardId.NEGATIVE_PUNISHMENT, bob)
    _end_turn_quickly(match)

    from loaded_dice.economy import calculate_compensation, calculate_interest

    chips_before = bob.chips
    interest = calculate_interest(chips_before)
    compensation = calculate_compensation(
        match._previous_rotation_attacks.attacker_count_on(bob.name),
        match._previous_rotation_attacks.player_attacked(bob.name),
    )
    match.start_turn()
    assert bob.chips == chips_before + interest + compensation - NEGATIVE_PUNISHMENT_CHIP_LOSS
    assert bob.queued_hindrances == []


def test_score_penalty_floors_at_zero():
    from loaded_dice.effects import TurnEffects
    from loaded_dice.scoring import apply_turn_modifiers, score_hand

    effects = TurnEffects(score_penalty=20)
    dice = [1, 1, 1, 1, 1]
    assert apply_turn_modifiers(score_hand(dice, Category.ONES), Category.ONES, effects) == 0

"""Trading card passives and activations."""

import pytest

from loaded_dice.card_effects.trading import (
    GAMBLER_BASE_COST,
    GAMBLER_COST_STEP,
    GECKO_COMPENSATION_BONUS,
    MERCHANT_CHIPS_PER_TURN,
    PERSUADER_SCORE_BONUS,
)
from loaded_dice.cards import CardId, card_for_id
from loaded_dice.economy import COMPENSATION_PACIFIST_CHIPS
from loaded_dice.match import Match, MatchConfig, WrongPhaseError
from loaded_dice.scoring import Category


def _begin_active_turn(match: Match) -> None:
    match.start_turn()
    match.begin_rolling()


def test_persuader_adds_score_bonus():
    match = Match(["Alice"])
    match.players[0].inventory.add_trading(card_for_id(CardId.PERSUADER))
    match.start_turn()
    assert match.players[0].turn_effects.score_bonus == PERSUADER_SCORE_BONUS


def test_gecko_boosts_compensation():
    match = Match(["Alice", "Bob"], config=MatchConfig(max_rotations=5))
    alice = match.players[0]
    alice.inventory.add_trading(card_for_id(CardId.GECKO))
    # Finish a rotation so compensation can pay out (pacifist, no attacks).
    _begin_active_turn(match)
    match.roll()
    match.end_turn_without_scoring()
    _begin_active_turn(match)
    match.roll()
    match.end_turn_without_scoring()
    assert match.rotation_count == 1

    before = alice.chips
    match.start_turn()
    assert alice.chips == before + COMPENSATION_PACIFIST_CHIPS + GECKO_COMPENSATION_BONUS


def test_gambler_buys_extra_roll_and_raises_cost():
    match = Match(["Alice"])
    alice = match.players[0]
    alice.chips = 1000
    alice.inventory.add_trading(card_for_id(CardId.GAMBLER))
    _begin_active_turn(match)
    match.roll()
    assert match.dice is not None
    before_max = match.dice.max_rolls
    chips_before = alice.chips

    match.activate_trading_card(CardId.GAMBLER)
    assert alice.chips == chips_before - GAMBLER_BASE_COST
    assert alice.gambler_next_cost == GAMBLER_BASE_COST + GAMBLER_COST_STEP
    assert match.dice.max_rolls == before_max + 1
    assert alice.inventory.has_trading(CardId.GAMBLER)


def test_lawyer_ends_turn_and_enters_cooldown():
    match = Match(["Alice", "Bob"])
    alice = match.players[0]
    alice.inventory.add_trading(card_for_id(CardId.LAWYER))
    _begin_active_turn(match)
    match.roll()
    match.activate_trading_card(CardId.LAWYER)
    assert match.active_player.name == "Bob"
    assert alice.lawyer_cooldown_turns == 2

    # Cooldown ticks on Alice's own turn ends (2 intervening turns).
    _begin_active_turn(match)  # Bob
    match.roll()
    match.end_turn_without_scoring()
    assert alice.lawyer_cooldown_turns == 2

    _begin_active_turn(match)  # Alice — still on CD
    match.roll()
    with pytest.raises(WrongPhaseError, match="cooldown"):
        match.activate_trading_card(CardId.LAWYER)
    match.end_turn_without_scoring()
    assert alice.lawyer_cooldown_turns == 1

    _begin_active_turn(match)  # Bob
    match.roll()
    match.end_turn_without_scoring()

    _begin_active_turn(match)  # Alice — still on CD
    match.roll()
    with pytest.raises(WrongPhaseError, match="cooldown"):
        match.activate_trading_card(CardId.LAWYER)
    match.end_turn_without_scoring()
    assert alice.lawyer_cooldown_turns == 0

    _begin_active_turn(match)  # Bob
    match.roll()
    match.end_turn_without_scoring()

    _begin_active_turn(match)  # Alice — ready again
    match.roll()
    match.activate_trading_card(CardId.LAWYER)
    assert alice.lawyer_cooldown_turns == 2


def test_merchant_still_pays_at_turn_start():
    match = Match(["Alice"])
    match.players[0].inventory.add_trading(card_for_id(CardId.MERCHANT))
    match.start_turn()
    assert match.players[0].chips == MERCHANT_CHIPS_PER_TURN


def test_activate_trading_via_action():
    from loaded_dice.actions import apply_action

    match = Match(["Alice"])
    match.players[0].chips = 500
    match.players[0].inventory.add_trading(card_for_id(CardId.GAMBLER))
    _begin_active_turn(match)
    match.roll()
    chips_before = match.players[0].chips
    apply_action(match, "Alice", {"type": "activate_trading", "card_id": "gambler"})
    assert match.players[0].chips == chips_before - GAMBLER_BASE_COST


def test_toddler_locks_other_dice_and_grants_reroll():
    match = Match(["Alice"])
    alice = match.players[0]
    alice.inventory.add_trading(card_for_id(CardId.TODDLER))
    _begin_active_turn(match)
    match.roll()
    assert match.dice is not None
    before_max = match.dice.max_rolls
    match.activate_trading_card(CardId.TODDLER, die_indices=[0, 2])
    assert match.dice.max_rolls == before_max + 1
    assert match.dice.dice[0].locked is False
    assert match.dice.dice[2].locked is False
    assert match.dice.dice[1].locked is True
    assert match.dice.dice[3].locked is True
    assert match.dice.dice[4].locked is True


def test_psychic_queues_previews():
    match = Match(["Alice"])
    match.players[0].inventory.add_trading(card_for_id(CardId.PSYCHIC))
    _begin_active_turn(match)
    match.roll()
    match.activate_trading_card(CardId.PSYCHIC, die_indices=[1, 4])
    assert set(match.psychic_previews) == {1, 4}
    assert match.dice is not None
    assert set(match.dice.forced_next_values) == {1, 4}
    # Unlock all so both previews apply on the next roll.
    for i in range(5):
        match.unlock(i)
    previewed = dict(match.psychic_previews)
    match.roll()
    assert match.dice.values[1] == previewed[1]
    assert match.dice.values[4] == previewed[4]
    assert match.psychic_previews == {}


def test_guardian_blocks_hindrance_with_cooldown():
    match = Match(["Alice", "Bob"])
    alice = match.players[0]
    bob = match.players[1]
    bob.inventory.add_trading(card_for_id(CardId.GUARDIAN))
    alice.inventory.add_power(card_for_id(CardId.GLASS_HALF_FULL))
    _begin_active_turn(match)
    match.roll()
    match.cast_hindrance(CardId.GLASS_HALF_FULL, bob)
    match.end_turn_without_scoring()

    match.start_turn()  # Bob
    assert len(bob.queued_hindrances) == 1
    match.block_hindrance(0)
    assert bob.queued_hindrances == []
    assert bob.guardian_cooldown_turns == 2


def test_forecaster_reveals_only_to_active_holder():
    from loaded_dice.rooms import Room

    room = Room(code="ABCD", starting_chips=1000)
    room.add_player("Alice")
    room.add_player("Bob")
    room.start_match("Alice")
    assert room.match is not None
    alice = room.match.players[0]
    bob = room.match.players[1]
    alice.inventory.add_trading(card_for_id(CardId.FORECASTER))
    bob.inventory.add_power(card_for_id(CardId.GLASS_HALF_EMPTY))

    alice_view = room.public_state(viewer_name="Alice")
    assert alice_view["match"]["forecaster_reveals"] == {
        "Bob": ["glass_half_empty"],
    }
    bob_view = room.public_state(viewer_name="Bob")
    assert bob_view["match"]["forecaster_reveals"] is None

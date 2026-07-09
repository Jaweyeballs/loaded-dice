import pytest

from loaded_dice.actions import ActionError, apply_action
from loaded_dice.cards import Card, CardId, CardKind
from loaded_dice.match import Match, TurnPhase


def test_apply_action_start_and_roll():
    match = Match(["Alice", "Bob"])
    apply_action(match, "Alice", {"type": "start_turn"})
    apply_action(match, "Alice", {"type": "begin_rolling"})
    apply_action(match, "Alice", {"type": "roll"})
    assert match.phase == TurnPhase.TURN_ACTIVE
    assert match.dice is not None
    assert match.dice.rolls_this_turn == 1


def test_non_active_player_cannot_roll():
    match = Match(["Alice", "Bob"])
    apply_action(match, "Alice", {"type": "start_turn"})
    apply_action(match, "Alice", {"type": "begin_rolling"})
    with pytest.raises(ActionError, match="Only the active player"):
        apply_action(match, "Bob", {"type": "roll"})


def test_bob_can_use_shop_during_alice_turn():
    match = Match(["Alice", "Bob"])
    bob = match.players[1]
    bob.chips = 1000
    apply_action(match, "Alice", {"type": "start_turn"})
    apply_action(match, "Alice", {"type": "begin_rolling"})
    apply_action(match, "Bob", {"type": "buy", "stock_index": 0})
    assert len(bob.inventory.power_cards) + len(bob.inventory.trading_cards) == 1


def test_cast_power_icarus():
    match = Match(["Alice", "Bob"])
    match.players[0].inventory.add_power(Card(CardId.ICARUS, CardKind.POWER))
    apply_action(match, "Alice", {"type": "start_turn"})
    apply_action(match, "Alice", {"type": "begin_rolling"})
    apply_action(match, "Alice", {"type": "roll"})
    match.dice.dice[0].value = 5
    apply_action(match, "Alice", {"type": "cast_power", "card_id": "icarus", "die_index": 0})
    assert match.dice.dice[0].value == 6


def test_unknown_action_type():
    match = Match(["Alice"])
    with pytest.raises(ActionError, match="Unknown action type"):
        apply_action(match, "Alice", {"type": "dance"})

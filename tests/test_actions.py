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


def test_free_end_turn_action_removed():
    match = Match(["Alice", "Bob"])
    apply_action(match, "Alice", {"type": "start_turn"})
    apply_action(match, "Alice", {"type": "begin_rolling"})
    apply_action(match, "Alice", {"type": "roll"})
    with pytest.raises(ActionError, match="Unknown action type"):
        apply_action(match, "Alice", {"type": "end_turn"})
    assert match.phase == TurnPhase.TURN_ACTIVE


def test_lawyer_activate_ends_without_scoring():
    match = Match(["Alice", "Bob"])
    match.players[0].inventory.add_trading(Card(CardId.LAWYER, CardKind.TRADING))
    apply_action(match, "Alice", {"type": "start_turn"})
    apply_action(match, "Alice", {"type": "begin_rolling"})
    apply_action(match, "Alice", {"type": "roll"})
    apply_action(match, "Alice", {"type": "activate_trading", "card_id": "lawyer"})
    assert match.active_player.name == "Bob"
    assert match.players[0].lawyer_cooldown_turns == 2


def test_write_off_cast_ends_without_scoring():
    match = Match(["Alice", "Bob"])
    match.players[0].inventory.add_power(Card(CardId.WRITE_OFF, CardKind.POWER))
    apply_action(match, "Alice", {"type": "start_turn"})
    apply_action(match, "Alice", {"type": "begin_rolling"})
    apply_action(match, "Alice", {"type": "roll"})
    apply_action(match, "Alice", {"type": "cast_power", "card_id": "write_off"})
    assert match.active_player.name == "Bob"
    assert not match.players[0].inventory.has_power(CardId.WRITE_OFF)

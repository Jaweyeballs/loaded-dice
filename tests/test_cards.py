import pytest

from loaded_dice.cards import (
    Card,
    CardId,
    CardInventory,
    CardKind,
    DEFAULT_POWER_SLOTS,
    DEFAULT_TRADING_SLOTS,
    InventoryFullError,
    CardNotInInventoryError,
)
from loaded_dice.effects import TurnEffects
from loaded_dice.match import Match
from loaded_dice.preview import preview_scores
from loaded_dice.scoring import Category, ScoreSheet, apply_turn_modifiers, score_hand


def test_power_inventory_respects_slot_limit():
    inventory = CardInventory()
    for _ in range(DEFAULT_POWER_SLOTS):
        inventory.add_power(Card(CardId.ICARUS, CardKind.POWER))
    with pytest.raises(InventoryFullError):
        inventory.add_power(Card(CardId.PARRY, CardKind.POWER))


def test_transparent_power_card_does_not_use_slot():
    inventory = CardInventory()
    for _ in range(DEFAULT_POWER_SLOTS):
        inventory.add_power(Card(CardId.ICARUS, CardKind.POWER))
    inventory.add_power(Card(CardId.PARRY, CardKind.POWER, transparent=True))
    assert inventory.power_slots_used() == DEFAULT_POWER_SLOTS
    assert len(inventory.power_cards) == DEFAULT_POWER_SLOTS + 1


def test_trading_inventory_respects_slot_limit():
    inventory = CardInventory()
    for _ in range(DEFAULT_TRADING_SLOTS):
        inventory.add_trading(Card(CardId.MERCHANT, CardKind.TRADING))
    with pytest.raises(InventoryFullError):
        inventory.add_trading(Card(CardId.MERCHANT, CardKind.TRADING))


def test_consume_power_by_id_removes_one_card():
    inventory = CardInventory()
    inventory.add_power(Card(CardId.ICARUS, CardKind.POWER))
    inventory.add_power(Card(CardId.ICARUS, CardKind.POWER))
    consumed = inventory.consume_power_by_id(CardId.ICARUS)
    assert consumed.id == CardId.ICARUS
    assert len(inventory.power_cards) == 1


def test_consume_power_by_id_raises_when_missing():
    inventory = CardInventory()
    with pytest.raises(CardNotInInventoryError):
        inventory.consume_power_by_id(CardId.ICARUS)


def test_glass_half_full_zeros_upper_section():
    effects = TurnEffects(zero_upper=True)
    assert apply_turn_modifiers(score_hand([3, 3, 3, 1, 2], Category.THREES), Category.THREES, effects) == 0


def test_glass_half_empty_zeros_lower_section():
    effects = TurnEffects(zero_lower=True)
    dice = [2, 3, 4, 5, 6]
    assert apply_turn_modifiers(score_hand(dice, Category.LARGE_STRAIGHT), Category.LARGE_STRAIGHT, effects) == 0


def test_score_bonus_applies_after_zeroing():
    effects = TurnEffects(zero_upper=True, score_bonus=2)
    assert apply_turn_modifiers(9, Category.THREES, effects) == 2


def test_preview_applies_turn_effects():
    dice = [3, 3, 3, 1, 2]
    sheet = ScoreSheet()
    effects = TurnEffects(zero_upper=True)
    previews = preview_scores(dice, sheet, effects)
    assert previews[Category.THREES] == 0
    assert previews[Category.CHANCE] == 12


def test_match_score_applies_turn_effects():
    match = Match(["Alice"])
    match.start_turn()
    match.begin_rolling()
    match.roll()
    for die, value in zip(match.dice.dice, [1, 2, 3, 4, 5]):
        die.value = value
    match.active_player.turn_effects = TurnEffects(score_bonus=2)
    match.score(Category.CHANCE)
    assert match.players[0].current_sheet.get_score(Category.CHANCE) == 17

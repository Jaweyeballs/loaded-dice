import random

import pytest

from loaded_dice.card_effects.trading import MERCHANT_CHIPS_PER_TURN
from loaded_dice.cards import CardId, CardKind, card_for_id
from loaded_dice.match import Match, MatchConfig, TurnPhase
from loaded_dice.scoring import Category
from loaded_dice.shop import SHOP_REROLL_COST, Shop, ShopError


def _begin_active_turn(match: Match) -> None:
    match.start_turn()


def test_shop_buy_adds_trading_card():
    shop = Shop.create(full_catalog=True)
    from loaded_dice.match import Player

    player = Player(name="Alice", chips=500)
    merchant_index = next(
        i for i, offer in enumerate(shop.stock) if offer and offer.card_id == CardId.MERCHANT
    )
    card = shop.buy(player, merchant_index)
    assert card.id == CardId.MERCHANT
    assert player.inventory.has_trading(CardId.MERCHANT)
    assert player.chips == 100
    assert shop.stock[merchant_index] is None


def test_shop_buy_sold_out_cannot_rebuy():
    shop = Shop.create(full_catalog=True)
    from loaded_dice.match import Player

    player = Player(name="Alice", chips=10_000)
    merchant_index = next(
        i for i, offer in enumerate(shop.stock) if offer and offer.card_id == CardId.MERCHANT
    )
    shop.buy(player, merchant_index)
    with pytest.raises(ShopError, match="Sold out"):
        shop.buy(player, merchant_index)


def test_shop_buy_refunds_on_full_inventory():
    shop = Shop.create(full_catalog=True)
    from loaded_dice.match import Player

    player = Player(name="Alice", chips=10_000)
    for _ in range(3):
        player.inventory.add_trading(card_for_id(CardId.MERCHANT))
    merchant_index = next(
        i for i, offer in enumerate(shop.stock) if offer and offer.card_id == CardId.MERCHANT
    )
    chips_before = player.chips
    with pytest.raises(ShopError):
        shop.buy(player, merchant_index)
    assert player.chips == chips_before
    assert shop.stock[merchant_index] is not None


def test_merchant_pays_chips_at_turn_start():
    match = Match(["Alice"])
    merchant = card_for_id(CardId.MERCHANT)
    match.players[0].inventory.add_trading(merchant)
    match.start_turn()
    assert match.players[0].chips == MERCHANT_CHIPS_PER_TURN


def test_active_player_can_shop_between_turns():
    match = Match(["Alice", "Bob"])
    _begin_active_turn(match)
    match.roll()
    match.score(Category.CHANCE)
    assert match.phase == TurnPhase.BETWEEN_TURNS
    assert match.can_use_shop(match.players[0])


def test_active_player_cannot_shop_during_turn():
    match = Match(["Alice", "Bob"])
    _begin_active_turn(match)
    assert not match.can_use_shop(match.active_player)


def test_other_player_can_shop_during_active_turn():
    match = Match(["Alice", "Bob"])
    _begin_active_turn(match)
    bob = match.players[1]
    assert match.active_player.name == "Alice"
    assert match.can_use_shop(bob)


def test_buy_from_shop_through_match():
    match = Match(["Alice", "Bob"])
    _begin_active_turn(match)
    match.roll()
    match.score(Category.CHANCE)
    alice = match.players[0]
    alice.chips = 500
    merchant_index = next(
        i
        for i, offer in enumerate(alice.shop.stock)
        if offer and offer.card_id == CardId.MERCHANT
    )
    card = match.buy_from_shop(alice, merchant_index)
    assert card.kind == CardKind.TRADING
    assert alice.inventory.has_trading(CardId.MERCHANT)
    assert alice.shop.stock[merchant_index] is None
    assert alice.last_chip_spend == 400


def test_normal_mode_shop_has_three_slots():
    match = Match(["Alice"], config=MatchConfig(dev_mode=False))
    assert len(match.players[0].shop.stock) == 3
    assert match.players[0].shop.full_catalog is False


def test_reroll_shop_changes_stock():
    random.seed(0)
    match = Match(["Alice", "Bob"], config=MatchConfig(dev_mode=False))
    _begin_active_turn(match)
    match.roll()
    match.score(Category.CHANCE)
    bob = match.players[1]
    bob.chips = 500
    before = [offer.card_id if offer else None for offer in bob.shop.stock]
    match.reroll_shop(bob)
    after = [offer.card_id if offer else None for offer in bob.shop.stock]
    assert bob.chips == 500 - SHOP_REROLL_COST
    assert before != after
    assert all(slot is not None for slot in bob.shop.stock)


def test_reroll_shop_is_per_player():
    random.seed(1)
    match = Match(["Alice", "Bob"], config=MatchConfig(dev_mode=False))
    _begin_active_turn(match)
    match.roll()
    match.score(Category.CHANCE)
    alice, bob = match.players
    alice.chips = 500
    bob.chips = 500
    bob_before = [offer.card_id if offer else None for offer in bob.shop.stock]
    alice_before = [offer.card_id if offer else None for offer in alice.shop.stock]
    match.reroll_shop(alice)
    assert [offer.card_id if offer else None for offer in bob.shop.stock] == bob_before
    assert [
        offer.card_id if offer else None for offer in alice.shop.stock
    ] != alice_before

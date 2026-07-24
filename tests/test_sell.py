from loaded_dice.actions import apply_action
from loaded_dice.cards import Card, CardId, CardKind, card_for_id
from loaded_dice.match import Match
from loaded_dice.shop import CARD_PRICES, sell_price_for_card


def test_sell_price_normal_is_shop_minus_100():
    card = card_for_id(CardId.ICARUS)
    assert sell_price_for_card(card) == max(0, CARD_PRICES[CardId.ICARUS] - 100)


def test_sell_price_transparent_doubles_shop_price():
    card = Card(CardId.PARRY, CardKind.POWER, transparent=True)
    assert sell_price_for_card(card) == CARD_PRICES[CardId.PARRY] * 2


def test_sell_card_pays_chips_anytime():
    match = Match(["Alice", "Bob"])
    bob = match.players[1]
    bob.chips = 0
    bob.inventory.add_power(card_for_id(CardId.ICARUS))
    # Alice is active / between turns — Bob can still sell.
    payout = match.sell_card(bob, kind="power", index=0)
    assert payout == max(0, CARD_PRICES[CardId.ICARUS] - 100)
    assert bob.chips == payout
    assert bob.inventory.power_cards == []


def test_sell_card_via_action_from_non_active_player():
    match = Match(["Alice", "Bob"])
    bob = match.players[1]
    bob.inventory.add_trading(card_for_id(CardId.MERCHANT))
    apply_action(
        match,
        "Bob",
        {"type": "sell_card", "kind": "trading", "index": 0},
    )
    assert bob.inventory.trading_cards == []
    assert bob.chips == max(0, CARD_PRICES[CardId.MERCHANT] - 100)

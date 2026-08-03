"""Shop — browse and buy cards between turns."""

from __future__ import annotations

from dataclasses import dataclass, field
import random

from loaded_dice.cards import Card, CardId, CardKind, InventoryFullError, card_for_id
from loaded_dice.economy import InsufficientChipsError

SHOP_REROLL_COST = 100

# Stub prices until rarity tiers are designed.
CARD_PRICES: dict[CardId, int] = {
    CardId.MERCHANT: 400,
    CardId.GAMBLER: 350,
    CardId.LAWYER: 300,
    CardId.PERSUADER: 450,
    CardId.GECKO: 400,
    CardId.TODDLER: 350,
    CardId.PSYCHIC: 350,
    CardId.GUARDIAN: 400,
    CardId.FORECASTER: 450,
    CardId.PARRY: 300,
    CardId.ICARUS: 250,
    CardId.SUPER_SERUM: 300,
    CardId.DO_OVER: 350,
    CardId.BENCHWARMER: 300,
    CardId.HELPING_HAND: 350,
    CardId.TWINS: 300,
    CardId.SPACE_DIE: 400,
    CardId.BOOLEAN: 350,
    CardId.WRITE_OFF: 250,
    CardId.POSITIVE_REINFORCEMENT: 300,
    CardId.NEGATIVE_REINFORCEMENT: 300,
    CardId.GLASS_HALF_EMPTY: 350,
    CardId.GLASS_HALF_FULL: 350,
    CardId.POSITIVE_PUNISHMENT: 350,
    CardId.NEGATIVE_PUNISHMENT: 350,
    CardId.BLUE_SHELL: 400,
    CardId.ALREADY_IN_JAIL: 350,
    CardId.SMOKE_BOMB: 350,
    CardId.TAX_AUDIT: 100,
    CardId.BOUNTY_NOTICE: 250,
    CardId.PROVOKE: 350,
    CardId.MIXUP: 450,
}

# Temporary testing override: None = entire catalog in stock. Set back to 3 later.
SHOP_STOCK_SIZE: int | None = None

SELL_PRICE_DISCOUNT = 100


def sell_price_for_card(card: Card) -> int:
    """Chips gained when selling *card* from inventory.

    Normal cards sell for shop price − 100 (floored at 0).
    Transparent cards sell for double the shop price.
    """
    shop_price = CARD_PRICES.get(card.id, 0)
    if card.transparent:
        return shop_price * 2
    return max(0, shop_price - SELL_PRICE_DISCOUNT)


class ShopError(Exception):
    """Raised when a shop action is invalid."""


@dataclass(frozen=True)
class ShopOffer:
    card_id: CardId
    price: int


def _offers_for_ids(card_ids: list[CardId] | tuple[CardId, ...]) -> list[ShopOffer]:
    return [ShopOffer(card_id, CARD_PRICES[card_id]) for card_id in card_ids]


def draw_stock(*, shuffle_full_catalog: bool = False) -> list[ShopOffer]:
    """Build shop stock for one player.

    While ``SHOP_STOCK_SIZE`` is None (playtest), stock is the full catalog.
    Otherwise each player gets a random unique draw of that many cards.
    """
    from loaded_dice.cards import CARD_DEFS

    if SHOP_STOCK_SIZE is None:
        pool = list(CARD_PRICES.keys())
        if shuffle_full_catalog:
            random.shuffle(pool)
        return _offers_for_ids(pool)
    pool = list(CARD_DEFS.keys())
    random.shuffle(pool)
    return _offers_for_ids(pool[:SHOP_STOCK_SIZE])


def default_stock() -> list[ShopOffer]:
    """Initial per-player shop stock."""
    return draw_stock(shuffle_full_catalog=False)


@dataclass
class Shop:
    """One player's personal shop — stock and rerolls are never shared."""

    stock: list[ShopOffer] = field(default_factory=default_stock)
    reroll_cost: int = SHOP_REROLL_COST

    def buy(self, player, index: int) -> Card:
        """Spend chips and add the offered card to *player*'s inventory."""
        if index < 0 or index >= len(self.stock):
            raise ShopError(f"No shop offer at index {index}")

        offer = self.stock[index]
        card = card_for_id(offer.card_id)

        try:
            player.spend_chips(offer.price)
        except InsufficientChipsError as exc:
            raise ShopError(str(exc)) from exc

        try:
            if card.kind == CardKind.POWER:
                player.inventory.add_power(card)
            else:
                player.inventory.add_trading(card)
        except InventoryFullError as exc:
            player.earn_chips(offer.price)
            raise ShopError(str(exc)) from exc

        return card

    def reroll_stock(self, player) -> list[ShopOffer]:
        """Pay to replace *this* player's shop stock with a fresh draw."""
        player.spend_chips(self.reroll_cost)
        self.stock = draw_stock(shuffle_full_catalog=True)
        return self.stock

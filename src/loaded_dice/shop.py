"""Shop — browse and buy cards between turns."""

from __future__ import annotations

from dataclasses import dataclass, field
import random

from loaded_dice.cards import Card, CardId, CardKind, InventoryFullError, card_for_id
from loaded_dice.economy import InsufficientChipsError

SHOP_REROLL_COST = 100
NORMAL_STOCK_SIZE = 3
DEV_STARTING_CHIPS = 9999

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


def _offers_for_ids(card_ids: list[CardId]) -> list[ShopOffer | None]:
    return [ShopOffer(card_id, CARD_PRICES[card_id]) for card_id in card_ids]


def draw_stock(*, full_catalog: bool) -> list[ShopOffer | None]:
    """Build shop stock for one player.

    *full_catalog* (dev mode): every priced card once.
    Otherwise: a random draw of ``NORMAL_STOCK_SIZE`` unique cards.
    """
    pool = list(CARD_PRICES.keys())
    random.shuffle(pool)
    if full_catalog:
        return _offers_for_ids(pool)
    return _offers_for_ids(pool[:NORMAL_STOCK_SIZE])


@dataclass
class Shop:
    """One player's personal shop — stock and rerolls are never shared."""

    stock: list[ShopOffer | None] = field(default_factory=list)
    reroll_cost: int = SHOP_REROLL_COST
    full_catalog: bool = False

    @classmethod
    def create(cls, *, full_catalog: bool = False) -> Shop:
        return cls(
            stock=draw_stock(full_catalog=full_catalog),
            full_catalog=full_catalog,
        )

    def buy(self, player, index: int) -> Card:
        """Spend chips, add the card, and mark the slot sold out."""
        if index < 0 or index >= len(self.stock):
            raise ShopError(f"No shop offer at index {index}")

        offer = self.stock[index]
        if offer is None:
            raise ShopError("Sold out")

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

        self.stock[index] = None
        return card

    def reroll_stock(self, player) -> list[ShopOffer | None]:
        """Pay to restock empty slots and replace any unbought offers."""
        player.spend_chips(self.reroll_cost)
        self.stock = draw_stock(full_catalog=self.full_catalog)
        return self.stock

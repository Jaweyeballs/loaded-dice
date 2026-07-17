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
}

# Playtest-friendly mix: power, trading activate, trading passive.
DEFAULT_STOCK_IDS: tuple[CardId, ...] = (
    CardId.ICARUS,
    CardId.GAMBLER,
    CardId.MERCHANT,
)


class ShopError(Exception):
    """Raised when a shop action is invalid."""


@dataclass(frozen=True)
class ShopOffer:
    card_id: CardId
    price: int


def default_stock() -> list[ShopOffer]:
    return [ShopOffer(card_id, CARD_PRICES[card_id]) for card_id in DEFAULT_STOCK_IDS]


@dataclass
class Shop:
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
        """Pay to replace shop stock with a fresh random draw from the catalog."""
        from loaded_dice.cards import CARD_DEFS

        player.spend_chips(self.reroll_cost)
        pool = list(CARD_DEFS.keys())
        random.shuffle(pool)
        self.stock = [ShopOffer(card_id, CARD_PRICES[card_id]) for card_id in pool[:3]]
        return self.stock

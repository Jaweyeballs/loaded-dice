"""Card definitions and player inventory."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


DEFAULT_POWER_SLOTS = 5
DEFAULT_TRADING_SLOTS = 3


class CardKind(Enum):
    POWER = "power"
    TRADING = "trading"


class CardId(Enum):
    """Known cards — expand as effects are implemented."""

    ICARUS = "icarus"
    MERCHANT = "merchant"
    PARRY = "parry"
    GLASS_HALF_EMPTY = "glass_half_empty"
    GLASS_HALF_FULL = "glass_half_full"


@dataclass(frozen=True)
class Card:
    id: CardId
    kind: CardKind
    transparent: bool = False


CARD_DEFS: dict[CardId, Card] = {
    CardId.MERCHANT: Card(CardId.MERCHANT, CardKind.TRADING),
    CardId.PARRY: Card(CardId.PARRY, CardKind.POWER),
    CardId.ICARUS: Card(CardId.ICARUS, CardKind.POWER),
    CardId.GLASS_HALF_EMPTY: Card(CardId.GLASS_HALF_EMPTY, CardKind.POWER),
    CardId.GLASS_HALF_FULL: Card(CardId.GLASS_HALF_FULL, CardKind.POWER),
}

# Positive powers that benefit another player — require target= in kwargs when implemented.
POSITIVE_POWERS_REQUIRING_TARGET: frozenset[CardId] = frozenset()

# Negative powers — cast via Match.cast_hindrance() (M2), not cast_power_card().
NEGATIVE_POWER_IDS: frozenset[CardId] = frozenset(
    {CardId.GLASS_HALF_EMPTY, CardId.GLASS_HALF_FULL}
)


def card_for_id(card_id: CardId) -> Card:
    return CARD_DEFS[card_id]


class InventoryFullError(Exception):
    """Raised when a player cannot hold another card of that type."""


class CardNotInInventoryError(Exception):
    """Raised when a player does not have the requested card."""


@dataclass
class CardInventory:
    power_cards: list[Card] = field(default_factory=list)
    trading_cards: list[Card] = field(default_factory=list)
    power_slot_limit: int = DEFAULT_POWER_SLOTS
    trading_slot_limit: int = DEFAULT_TRADING_SLOTS

    def power_slots_used(self) -> int:
        return sum(1 for card in self.power_cards if not card.transparent)

    def trading_slots_used(self) -> int:
        return len(self.trading_cards)

    def can_add_power(self, card: Card) -> bool:
        if card.kind != CardKind.POWER:
            return False
        if card.transparent:
            return True
        return self.power_slots_used() < self.power_slot_limit

    def can_add_trading(self, card: Card) -> bool:
        if card.kind != CardKind.TRADING:
            return False
        return self.trading_slots_used() < self.trading_slot_limit

    def add_power(self, card: Card) -> None:
        if not self.can_add_power(card):
            raise InventoryFullError("No open power card slots")
        self.power_cards.append(card)

    def add_trading(self, card: Card) -> None:
        if not self.can_add_trading(card):
            raise InventoryFullError("No open trading card slots")
        self.trading_cards.append(card)

    def has_power(self, card_id: CardId) -> bool:
        return any(card.id == card_id for card in self.power_cards)

    def consume_power_by_id(self, card_id: CardId) -> Card:
        """Remove and return one power card with *card_id* (consumable use)."""
        for index, card in enumerate(self.power_cards):
            if card.id == card_id:
                return self.power_cards.pop(index)
        raise CardNotInInventoryError(f"No {card_id.value} in power inventory")

    def remove_power(self, card: Card) -> None:
        self.power_cards.remove(card)

    def remove_trading(self, card: Card) -> None:
        self.trading_cards.remove(card)

    def has_trading(self, card_id: CardId) -> bool:
        return any(card.id == card_id for card in self.trading_cards)

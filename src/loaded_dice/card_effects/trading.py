"""Trading card effects — passive income and scoring modifiers."""

from __future__ import annotations

from typing import TYPE_CHECKING, Callable

from loaded_dice.cards import CardId
from loaded_dice.effects import TurnEffects

if TYPE_CHECKING:
    from loaded_dice.match import Match, Player

# --- Constants (balance here) ---

MERCHANT_CHIPS_PER_TURN = 200

# --- Turn-start handlers (income, reveals, etc.) ---


def _merchant_on_turn_start(player: Player, match: Match | None = None) -> None:
    player.earn_chips(MERCHANT_CHIPS_PER_TURN)


TRADING_ON_TURN_START: dict[CardId, Callable[[Player, Match | None], None]] = {
    CardId.MERCHANT: _merchant_on_turn_start,
}


def apply_trading_turn_start(player: Player, match: Match | None = None) -> None:
    """Run turn-start handlers for each trading card in the player's party."""
    seen: set[CardId] = set()
    for card in player.inventory.trading_cards:
        if card.id in seen:
            continue
        seen.add(card.id)
        handler = TRADING_ON_TURN_START.get(card.id)
        if handler is not None:
            handler(player, match)


# --- Scoring modifiers (fold into TurnEffects at resolve time) ---


def apply_trading_scoring_modifiers(player: Player, effects: TurnEffects) -> None:
    """Apply passive scoring changes from trading cards to *effects*."""
    # Persuader (+3): effects.score_bonus += 3 when implemented.

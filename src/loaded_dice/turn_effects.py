"""Resolve turn-scoped effects — thin glue over card_effects registries."""

from __future__ import annotations

from typing import TYPE_CHECKING

from loaded_dice.card_effects.trading import (
    apply_trading_scoring_modifiers,
    apply_trading_turn_start,
)
from loaded_dice.effects import TurnEffects

if TYPE_CHECKING:
    from loaded_dice.match import Match, Player


def resolve_turn_effects(player: Player) -> TurnEffects:
    """Build scoring modifiers for this turn from passive cards (not hindrances)."""
    effects = TurnEffects()
    apply_trading_scoring_modifiers(player, effects)
    return effects


def apply_turn_start_passives(player: Player, match: Match | None = None) -> None:
    """One-shot triggers at the start of a player's turn (trading cards, etc.)."""
    apply_trading_turn_start(player, match)

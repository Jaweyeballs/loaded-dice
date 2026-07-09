"""Serialize Match state for API / WebSocket clients."""

from __future__ import annotations

from typing import Any

from loaded_dice.match import Match, Player
from loaded_dice.preview import preview_scores
from loaded_dice.scoring import Category


def serialize_card(card) -> dict[str, Any]:
    return {
        "id": card.id.value,
        "kind": card.kind.value,
        "transparent": card.transparent,
    }


def serialize_player(player: Player, match: Match) -> dict[str, Any]:
    sheet = {
        category.value: player.current_sheet.get_score(category)
        for category in Category
    }
    return {
        "name": player.name,
        "chips": player.chips,
        "total_score": player.total_score(),
        "game_total": player.game_total,
        "sheet": sheet,
        "power_cards": [serialize_card(c) for c in player.inventory.power_cards],
        "trading_cards": [serialize_card(c) for c in player.inventory.trading_cards],
        "queued_hindrances": [
            {
                "card_id": h.card_id.value,
                "caster_name": h.caster_name,
            }
            for h in player.queued_hindrances
        ],
        "turn_effects": {
            "zero_upper": player.turn_effects.zero_upper,
            "zero_lower": player.turn_effects.zero_lower,
            "score_bonus": player.turn_effects.score_bonus,
            "score_penalty": player.turn_effects.score_penalty,
        },
        "parry_ready": player.parry_ready,
        "can_use_shop": match.can_use_shop(player),
    }


def serialize_dice(match: Match) -> dict[str, Any] | None:
    if match.dice is None:
        return None
    dice = match.dice
    return {
        "values": dice.values,
        "locked": [die.locked for die in dice.dice],
        "rolls_this_turn": dice.rolls_this_turn,
        "max_rolls": dice.max_rolls,
    }


def serialize_shop(match: Match) -> dict[str, Any]:
    return {
        "stock": [
            {"index": i, "card_id": offer.card_id.value, "price": offer.price}
            for i, offer in enumerate(match.shop.stock)
        ],
        "reroll_cost": match.shop.reroll_cost,
    }


def serialize_previews(match: Match) -> dict[str, int] | None:
    if match.dice is None or match.dice.rolls_this_turn < 1:
        return None
    try:
        previews = preview_scores(
            match.dice.values,
            match.active_player.current_sheet,
            match.active_player.turn_effects,
        )
    except ValueError:
        return None
    return {category.value: points for category, points in previews.items()}


def serialize_match(match: Match) -> dict[str, Any]:
    winner = match.winner()
    return {
        "phase": match.phase.value,
        "rotation_count": match.rotation_count,
        "active_player": match.active_player.name,
        "is_over": match.is_over(),
        "winner": winner.name if winner else None,
        "players": [serialize_player(p, match) for p in match.players],
        "dice": serialize_dice(match),
        "shop": serialize_shop(match),
        "previews": serialize_previews(match),
    }

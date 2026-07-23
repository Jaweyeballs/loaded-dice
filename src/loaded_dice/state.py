"""Serialize Match state for API / WebSocket clients."""

from __future__ import annotations

from typing import Any

from loaded_dice.cards import CardId
from loaded_dice.card_effects.positive_power import compute_do_over_points
from loaded_dice.match import Match, Player
from loaded_dice.preview import SCORING_HAND_SIZE, preview_scores
from loaded_dice.scoring import Category, YAHTZEE_BONUS_POINTS, is_yahtzee
from itertools import combinations


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
        "score_delta": match.score_delta_this_rotation(player),
        "game_total": player.game_total,
        "sheet": sheet,
        "last_scored_category": (
            player.last_scored_category.value
            if player.last_scored_category is not None
            else None
        ),
        "upper_subtotal": player.current_sheet.upper_subtotal(),
        "upper_bonus": player.current_sheet.upper_bonus(),
        "lower_subtotal": player.current_sheet.lower_subtotal(),
        "yahtzee_bonus_count": (
            player.current_sheet.yahtzee_bonuses // YAHTZEE_BONUS_POINTS
            if player.current_sheet.yahtzee_bonuses
            else 0
        ),
        "sheet_total": player.current_sheet.grand_total(),
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
        "gambler_cost": player.gambler_next_cost,
        "lawyer_cooldown": player.lawyer_cooldown_turns,
        "guardian_cooldown": player.guardian_cooldown_turns,
        "attacked_last_rotation": match.player_attacked_last_rotation(player),
        "attacked_by_last_rotation": sorted(
            match.attackers_on_player_last_rotation(player)
        ),
    }


def serialize_dice(match: Match) -> dict[str, Any] | None:
    if match.dice is None:
        return None
    dice = match.dice
    return {
        "values": dice.values,
        "locked": [die.locked for die in dice.dice],
        "kinds": [die.kind for die in dice.dice],
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


def serialize_do_over_preview(match: Match) -> dict[str, Any] | None:
    """Preview for overwriting the active player's last scored category via Do over."""
    if match.dice is None or match.dice.rolls_this_turn < 1:
        return None
    player = match.active_player
    category = player.last_scored_category
    if category is None or category == Category.YAHTZEE:
        return None
    if not player.inventory.has_power(CardId.DO_OVER):
        return None
    values = match.dice.values
    if len(values) < SCORING_HAND_SIZE:
        return None
    # Exact 5-die yahtzee: block Do over when Yahtzee box is already filled.
    if len(values) == SCORING_HAND_SIZE and is_yahtzee(values) and not (
        player.current_sheet.is_available(Category.YAHTZEE)
    ):
        return None
    try:
        if len(values) == SCORING_HAND_SIZE:
            points = compute_do_over_points(values, category, player.turn_effects)
        else:
            points = max(
                compute_do_over_points(
                    [values[i] for i in indices],
                    category,
                    player.turn_effects,
                )
                for indices in combinations(range(len(values)), SCORING_HAND_SIZE)
            )
    except ValueError:
        return None
    return {"category": category.value, "points": points}


def serialize_match(match: Match) -> dict[str, Any]:
    winner = match.winner()
    return {
        "phase": match.phase.value,
        "rotation_count": match.rotation_count,
        "active_player": match.active_player.name,
        "is_over": match.is_over(),
        "winner": winner.name if winner else None,
        "leaderboard_order": match.leaderboard_order,
        "players": [serialize_player(p, match) for p in match.players],
        "dice": serialize_dice(match),
        "shop": serialize_shop(match),
        "previews": serialize_previews(match),
        "do_over_preview": serialize_do_over_preview(match),
        "psychic_previews": {
            str(index): face for index, face in match.psychic_previews.items()
        },
        "hindrance_feed": [
            {
                "card_id": entry.card_id.value,
                "caster_name": entry.caster_name,
                "target_name": entry.target_name,
                "rotation": entry.rotation,
                "blocked": entry.blocked,
                "blocker_card_id": (
                    entry.blocker_card_id.value if entry.blocker_card_id else None
                ),
            }
            for entry in match.hindrance_feed
        ],
    }

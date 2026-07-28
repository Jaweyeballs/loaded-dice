"""Serialize Match state for API / WebSocket clients."""

from __future__ import annotations

from typing import Any

from loaded_dice.cards import CardId
from loaded_dice.card_effects.positive_power import (
    POSITIVE_REINFORCEMENT_BONUS,
    compute_do_over_points,
)
from loaded_dice.card_effects.trading import PERSUADER_SCORE_BONUS
from loaded_dice.match import Match, Player, TurnPhase
from loaded_dice.preview import SCORING_HAND_SIZE, preview_scores
from loaded_dice.scoring import Category, YAHTZEE_BONUS_POINTS, is_yahtzee
from loaded_dice.effects import TurnEffects
from loaded_dice.shop import sell_price_for_card
from itertools import combinations
from dataclasses import replace


def effective_turn_effects(player: Player, match: Match | None = None) -> TurnEffects:
    """Turn effects including pending punishment and held Positive Reinforcement."""
    effects = player.turn_effects
    score_penalty = effects.score_penalty + player.pending_score_penalty
    score_bonus = effects.score_bonus
    if (
        match is not None
        and match.rotation_count > 0
        and match.player_qualifies_as_pacifist(player)
        and player.inventory.has_power(CardId.POSITIVE_REINFORCEMENT)
    ):
        score_bonus += POSITIVE_REINFORCEMENT_BONUS
    if score_penalty == effects.score_penalty and score_bonus == effects.score_bonus:
        return effects
    return replace(effects, score_penalty=score_penalty, score_bonus=score_bonus)


def serialize_card(card) -> dict[str, Any]:
    return {
        "id": card.id.value,
        "kind": card.kind.value,
        "transparent": card.transparent,
        "sell_price": sell_price_for_card(card),
    }


def serialize_score_breakdown(player: Player, match: Match) -> dict[str, Any] | None:
    """Signed score modifiers for the scoresheet HUD (cleared after they score)."""
    lines: list[dict[str, Any]] = []
    hh = player.turn_effects.helping_hand_bonus
    if hh > 0:
        lines.append({"label": "helping hand", "amount": hh})
    if player.pending_score_penalty > 0:
        lines.append(
            {
                "label": "positive punishment",
                "amount": -player.pending_score_penalty,
            }
        )

    active_hand = (
        match.phase == TurnPhase.TURN_ACTIVE and player is match.active_player
    )
    if active_hand:
        if player.inventory.has_trading(CardId.PERSUADER):
            lines.append({"label": "persuader", "amount": PERSUADER_SCORE_BONUS})
        if (
            match.rotation_count > 0
            and match.player_qualifies_as_pacifist(player)
            and player.inventory.has_power(CardId.POSITIVE_REINFORCEMENT)
        ):
            lines.append(
                {
                    "label": "positive reinforcement",
                    "amount": POSITIVE_REINFORCEMENT_BONUS,
                }
            )
        # Any remaining turn penalty beyond pending (rare).
        if player.turn_effects.score_penalty > 0:
            lines.append(
                {
                    "label": "score penalty",
                    "amount": -player.turn_effects.score_penalty,
                }
            )
        remaining_bonus = (
            player.turn_effects.score_bonus - hh - (
                PERSUADER_SCORE_BONUS
                if player.inventory.has_trading(CardId.PERSUADER)
                else 0
            )
        )
        if remaining_bonus > 0:
            lines.append({"label": "score bonus", "amount": remaining_bonus})

    if not lines:
        return None
    net = sum(int(line["amount"]) for line in lines)
    return {"lines": lines, "net": net}


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
        "power_count": len(player.inventory.power_cards),
        "trading_count": len(player.inventory.trading_cards),
        "card_count": (
            len(player.inventory.power_cards) + len(player.inventory.trading_cards)
        ),
        "power_slots_used": len(player.inventory.power_cards),
        "power_slot_capacity": player.inventory.power_capacity(),
        "trading_slots_used": player.inventory.trading_slots_used(),
        "trading_slot_capacity": player.inventory.trading_capacity(),
        "power_cards": [serialize_card(c) for c in player.inventory.power_cards],
        "trading_cards": [serialize_card(c) for c in player.inventory.trading_cards],
        "queued_hindrances": [
            {
                "card_id": h.card_id.value,
                "caster_name": h.caster_name,
                "mixup": match.caster_has_mixup(h.caster_name),
                "active": h.active,
            }
            for h in player.queued_hindrances
        ],
        "turn_effects": {
            "zero_upper": player.turn_effects.zero_upper,
            "zero_lower": player.turn_effects.zero_lower,
            "score_bonus": player.turn_effects.score_bonus,
            "score_penalty": (
                player.turn_effects.score_penalty + player.pending_score_penalty
            ),
            "helping_hand_bonus": player.turn_effects.helping_hand_bonus,
        },
        "pending_score_penalty": player.pending_score_penalty,
        "score_breakdown": serialize_score_breakdown(player, match),
        "parry_ready": player.parry_ready,
        "can_use_shop": match.can_use_shop(player),
        "gambler_cost": player.gambler_next_cost,
        "lawyer_cooldown": player.lawyer_cooldown_turns,
        "guardian_cooldown": player.guardian_cooldown_turns,
        "attacked_last_rotation": match.player_attacked_last_rotation(player),
        "pacifist_qualified": match.player_qualifies_as_pacifist(player),
        "attacked_by_last_rotation": sorted(
            match.attackers_on_player_last_rotation(player)
        ),
        "last_turn_preview": (
            player.last_turn_preview.to_dict() if player.last_turn_preview else None
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
        # Parallel to values — legal faces for Space Die / UI (may be non-1–6).
        "faces": [list(die.faces) for die in dice.dice],
        "rolls_this_turn": dice.rolls_this_turn,
        "max_rolls": dice.max_rolls,
        "jail_locked_index": match.active_player.jail_locked_index,
        "smoke_bomb_locked_indices": list(
            match.active_player.smoke_bomb_locked_indices
        ),
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
            effective_turn_effects(match.active_player, match),
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
        effects = effective_turn_effects(player, match)
        if len(values) == SCORING_HAND_SIZE:
            points = compute_do_over_points(values, category, effects)
        else:
            points = max(
                compute_do_over_points(
                    [values[i] for i in indices],
                    category,
                    effects,
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
        "twins_links": {
            str(follower): leader
            for follower, leader in match.twins_links.items()
        },
        "toddler_used_this_turn": match.toddler_used_this_turn,
        "psychic_used_this_turn": match.psychic_used_this_turn,
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

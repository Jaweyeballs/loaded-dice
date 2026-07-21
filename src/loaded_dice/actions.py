"""Dispatch structured client actions onto a Match."""

from __future__ import annotations

from typing import Any, Callable

from loaded_dice.cards import CardId, CardNotInInventoryError, NEGATIVE_POWER_IDS, UNTARGETED_HINDRANCE_IDS
from loaded_dice.card_effects.positive_power import POSITIVE_POWER_CAST
from loaded_dice.dice import TooManyRollsError
from loaded_dice.economy import InsufficientChipsError
from loaded_dice.match import (
    InvalidDieSelectionError,
    Match,
    MatchOverError,
    MustRollBeforeScoreError,
    Player,
    WrongPhaseError,
)
from loaded_dice.scoring import Category
from loaded_dice.shop import ShopError

TURN_ACTIONS = frozenset(
    {
        "start_turn",
        "begin_rolling",
        "block_hindrance",
        "roll",
        "lock",
        "unlock",
        "cast_power",
        "cast_hindrance",
        "activate_trading",
        "score",
    }
)

SHOP_ACTIONS = frozenset({"buy", "reroll_shop"})


class ActionError(Exception):
    """Raised when a client action is invalid."""


def _parse_card_id(value: str) -> CardId:
    key = value.strip().lower().replace("-", "_")
    for card_id in CardId:
        if card_id.value == key:
            return card_id
    raise ActionError(f"Unknown card: {value}")


def _parse_category(value: str) -> Category:
    key = value.strip().lower().replace("-", "_")
    for category in Category:
        if category.value == key:
            return category
    raise ActionError(f"Unknown category: {value}")


def _player_by_name(match: Match, name: str) -> Player:
    for player in match.players:
        if player.name == name:
            return player
    raise ActionError(f"Unknown player: {name}")


def _require(action: dict[str, Any], key: str) -> Any:
    if key not in action:
        raise ActionError(f"Missing field: {key}")
    return action[key]


def _start_turn(match: Match, _actor: Player, _action: dict[str, Any]) -> None:
    match.start_turn()


def _begin_rolling(match: Match, _actor: Player, _action: dict[str, Any]) -> None:
    match.begin_rolling()


def _block_hindrance(match: Match, _actor: Player, action: dict[str, Any]) -> None:
    match.block_hindrance(int(_require(action, "hindrance_index")))


def _roll(match: Match, _actor: Player, _action: dict[str, Any]) -> None:
    match.roll()


def _lock(match: Match, _actor: Player, action: dict[str, Any]) -> None:
    match.lock(int(_require(action, "index")))


def _unlock(match: Match, _actor: Player, action: dict[str, Any]) -> None:
    match.unlock(int(_require(action, "index")))


def _cast_power(match: Match, _actor: Player, action: dict[str, Any]) -> None:
    card_id = _parse_card_id(str(_require(action, "card_id")))
    if card_id not in POSITIVE_POWER_CAST:
        raise ActionError(f"{card_id.value} is not a castable positive power card")
    kwargs: dict[str, Any] = {}
    if "die_index" in action and action["die_index"] is not None:
        kwargs["die_index"] = int(action["die_index"])
    if "face_value" in action and action["face_value"] is not None:
        kwargs["face_value"] = int(action["face_value"])
    if "die_indices" in action and action["die_indices"] is not None:
        kwargs["die_indices"] = [int(i) for i in action["die_indices"]]
    if "choice" in action and action["choice"] is not None:
        kwargs["choice"] = str(action["choice"])
    if "target" in action and action["target"] is not None:
        kwargs["target"] = _player_by_name(match, str(action["target"]))
    match.cast_power_card(card_id, **kwargs)


def _cast_hindrance(match: Match, _actor: Player, action: dict[str, Any]) -> None:
    card_id = _parse_card_id(str(_require(action, "card_id")))
    if card_id not in NEGATIVE_POWER_IDS:
        raise ActionError(f"{card_id.value} is not a castable hindrance")
    if card_id in UNTARGETED_HINDRANCE_IDS:
        match.cast_hindrance(card_id, target=None)
        return
    target = _player_by_name(match, str(_require(action, "target")))
    match.cast_hindrance(card_id, target)


def _activate_trading(match: Match, _actor: Player, action: dict[str, Any]) -> None:
    card_id = _parse_card_id(str(_require(action, "card_id")))
    kwargs: dict[str, Any] = {}
    if "die_indices" in action and action["die_indices"] is not None:
        kwargs["die_indices"] = [int(i) for i in action["die_indices"]]
    match.activate_trading_card(card_id, **kwargs)


def _score(match: Match, _actor: Player, action: dict[str, Any]) -> None:
    category = _parse_category(str(_require(action, "category")))
    die_indices = action.get("die_indices")
    if die_indices is not None:
        die_indices = [int(i) for i in die_indices]
    match.score(category, die_indices=die_indices)


def _buy(match: Match, actor: Player, action: dict[str, Any]) -> None:
    match.buy_from_shop(actor, int(_require(action, "stock_index")))


def _reroll_shop(match: Match, actor: Player, _action: dict[str, Any]) -> None:
    match.reroll_shop(actor)


HANDLERS: dict[str, Callable[[Match, Player, dict[str, Any]], None]] = {
    "start_turn": _start_turn,
    "begin_rolling": _begin_rolling,
    "block_hindrance": _block_hindrance,
    "roll": _roll,
    "lock": _lock,
    "unlock": _unlock,
    "cast_power": _cast_power,
    "cast_hindrance": _cast_hindrance,
    "activate_trading": _activate_trading,
    "score": _score,
    "buy": _buy,
    "reroll_shop": _reroll_shop,
}


def apply_action(match: Match, actor_name: str, action: dict[str, Any]) -> None:
    """Apply a structured action from *actor_name* to *match*."""
    if not isinstance(action, dict):
        raise ActionError("Action must be an object")
    action_type = action.get("type")
    if not action_type:
        raise ActionError("Missing action type")

    handler = HANDLERS.get(str(action_type))
    if handler is None:
        raise ActionError(f"Unknown action type: {action_type}")

    actor = _player_by_name(match, actor_name)

    if action_type in TURN_ACTIONS and actor is not match.active_player:
        raise ActionError("Only the active player can take this action")

    if action_type in SHOP_ACTIONS and not match.can_use_shop(actor):
        raise ActionError(f"{actor.name} cannot use the shop right now")

    try:
        handler(match, actor, action)
    except (
        ActionError,
        WrongPhaseError,
        MatchOverError,
        MustRollBeforeScoreError,
        InvalidDieSelectionError,
        TooManyRollsError,
        InsufficientChipsError,
        CardNotInInventoryError,
        ShopError,
        ValueError,
    ) as exc:
        raise ActionError(str(exc)) from exc

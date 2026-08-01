"""Interactive CLI sandbox for local playtesting."""

from __future__ import annotations

import argparse
import sys

from loaded_dice.card_effects.positive_power import POSITIVE_POWER_CAST
from loaded_dice.cards import NEGATIVE_POWER_IDS, CardId
from loaded_dice.match import Match, MatchConfig, Player, TurnPhase, WrongPhaseError
from loaded_dice.preview import preview_scores
from loaded_dice.scoring import Category

SANDBOX_STARTING_CHIPS = 1000

_CATEGORY_ALIASES = {category.value: category for category in Category}
_CATEGORY_ALIASES.update({str(index): category for index, category in enumerate(Category, start=1)})


def _parse_category(token: str) -> Category:
    key = token.strip().lower().replace("-", "_").replace(" ", "_")
    if key in _CATEGORY_ALIASES:
        return _CATEGORY_ALIASES[key]
    raise ValueError(f"Unknown category: {token}")


def _parse_card_id(token: str) -> CardId:
    key = token.strip().lower().replace("-", "_").replace(" ", "_")
    for card_id in CardId:
        if card_id.value == key:
            return card_id
    matches = [card_id for card_id in CardId if key in card_id.value]
    if len(matches) == 1:
        return matches[0]
    raise ValueError(f"Unknown card: {token}")


def _player_by_token(match: Match, token: str) -> Player:
    names = {player.name.lower(): player for player in match.players}
    if token.lower() in names:
        return names[token.lower()]
    if token.isdigit():
        index = int(token) - 1
        if 0 <= index < len(match.players):
            return match.players[index]
    raise ValueError(f"Unknown player: {token}")


def _die_status(match: Match) -> str:
    dice = match.dice
    if dice is None:
        return "(no dice)"
    parts = []
    for index, die in enumerate(dice.dice):
        lock = "L" if die.locked else " "
        parts.append(f"[{index}:{die.value}{lock}]")
    rolls = dice.rolls_this_turn
    return " ".join(parts) + f"  (rolls {rolls}/{dice.max_rolls})"


def _format_sheet(player: Player) -> str:
    lines = [f"  {player.name}: {player.total_score()} pts, {player.chips} chips"]
    for category in Category:
        marker = " " if player.current_sheet.is_available(category) else "x"
        score = player.current_sheet.get_score(category)
        display = "-" if score is None else str(score)
        lines.append(f"    {marker} {category.value:18} {display}")
    return "\n".join(lines)


def _format_inventory(player: Player) -> str:
    power = ", ".join(card.id.value for card in player.inventory.power_cards) or "(none)"
    trading = ", ".join(card.id.value for card in player.inventory.trading_cards) or "(none)"
    return f"  power: {power}\n  trading: {trading}"


def _print_status(match: Match) -> None:
    print(f"\n--- Rotation {match.rotation_count} | Phase: {match.phase.value} ---")
    print(f"Active: {match.active_player.name}")
    for player in match.players:
        print(_format_sheet(player))
    print("Inventory (active):")
    print(_format_inventory(match.active_player))
    if match.dice is not None:
        print(f"Dice: {_die_status(match)}")
    if match.active_player.queued_hindrances:
        print("Queued hindrances on active player:")
        for index, hindrance in enumerate(match.active_player.queued_hindrances):
            print(f"  [{index}] {hindrance.card_id.value} from {hindrance.caster_name}")
    if match.active_player.turn_effects.score_bonus or match.active_player.turn_effects.score_penalty:
        effects = match.active_player.turn_effects
        print(
            f"Turn modifiers: +{effects.score_bonus} / -{effects.score_penalty} "
            f"(zero upper={effects.zero_upper}, zero lower={effects.zero_lower})"
        )


def _print_shop(match: Match, player: Player) -> None:
    print("\nShop:")
    for index, offer in enumerate(player.shop.stock):
        print(f"  [{index}] {offer.card_id.value} — {offer.price} chips")
    print(f"  reroll stock costs {player.shop.reroll_cost} chips")


def _print_help() -> None:
    print(
        """
Commands:
  help                         Show this message
  status                       Show scores, chips, dice, inventory
  shop                         List shop stock (when open)
  buy <index>                  Buy from shop
  reroll                       Pay to refresh shop stock
  start                        Start turn / begin rolling
  roll                         Roll unlocked dice
  lock <index> | unlock <index>
  preview                      Best score per open category
  cast <card> [die_index=N]    Play a positive power card
  hindrance <card> <target>    Queue a negative power card
  block <index>                Parry a queued hindrance (turn start)
  score <category>             Score and end turn (name or 1-13)
  end                          End without scoring (requires Lawyer or Write off)
  quit                         Exit sandbox
"""
    )


def _handle_command(match: Match, line: str) -> bool:
    """Run one command. Returns False to quit."""
    parts = line.strip().split()
    if not parts:
        return True

    command = parts[0].lower()
    args = parts[1:]

    try:
        if command in {"help", "?"}:
            _print_help()
        elif command == "status":
            _print_status(match)
        elif command == "shop":
            viewer = match.active_player
            if not match.can_use_shop(viewer):
                print("Shop is not open for the active player right now.")
            else:
                _print_shop(match, viewer)
        elif command == "buy":
            if len(args) != 1:
                raise ValueError("Usage: buy <index>")
            card = match.buy_from_shop(match.active_player, int(args[0]))
            print(f"Bought {card.id.value}.")
        elif command == "reroll":
            match.reroll_shop(match.active_player)
            print("Shop stock refreshed.")
            _print_shop(match, match.active_player)
        elif command == "start":
            if match.phase == TurnPhase.BETWEEN_TURNS:
                match.start_turn()
                print(f"{match.active_player.name}'s turn — you can roll.")
            elif match.phase == TurnPhase.TURN_START:
                match.begin_rolling()
                print("Rolling phase started.")
            else:
                print("Already in the rolling phase.")
        elif command == "roll":
            values = match.roll()
            print(f"Rolled: {values}")
            print(f"Dice: {_die_status(match)}")
        elif command == "lock":
            if len(args) != 1:
                raise ValueError("Usage: lock <index>")
            match.lock(int(args[0]))
            print(f"Dice: {_die_status(match)}")
        elif command == "unlock":
            if len(args) != 1:
                raise ValueError("Usage: unlock <index>")
            match.unlock(int(args[0]))
            print(f"Dice: {_die_status(match)}")
        elif command == "preview":
            if match.dice is None:
                raise WrongPhaseError("No dice to preview")
            previews = preview_scores(
                match.dice.values,
                match.active_player.current_sheet,
                match.active_player.turn_effects,
            )
            for category, points in previews.items():
                print(f"  {category.value:18} {points}")
        elif command == "cast":
            if not args:
                raise ValueError("Usage: cast <card> [die_index=N]")
            card_id = _parse_card_id(args[0])
            if card_id not in POSITIVE_POWER_CAST:
                raise ValueError(f"{card_id.value} is not a castable positive power card")
            kwargs: dict = {}
            for arg in args[1:]:
                if arg.startswith("die_index="):
                    kwargs["die_index"] = int(arg.split("=", 1)[1])
                else:
                    raise ValueError(f"Unknown cast option: {arg}")
            match.cast_power_card(card_id, **kwargs)
            print(f"Cast {card_id.value}.")
            if match.dice is not None:
                print(f"Dice: {_die_status(match)}")
        elif command == "hindrance":
            if len(args) != 2:
                raise ValueError("Usage: hindrance <card> <target>")
            card_id = _parse_card_id(args[0])
            target = _player_by_token(match, args[1])
            match.cast_hindrance(card_id, target)
            print(f"Queued {card_id.value} on {target.name}.")
        elif command == "block":
            if len(args) != 1:
                raise ValueError("Usage: block <hindrance_index>")
            match.block_hindrance(int(args[0]))
            print("Hindrance blocked.")
        elif command == "score":
            if not args:
                raise ValueError("Usage: score <category>")
            category = _parse_category(args[0])
            points = match.score(category)
            print(f"Scored {points} in {category.value}.")
        elif command == "end":
            player = match.active_player
            if player.inventory.has_trading(CardId.LAWYER) and player.lawyer_cooldown_turns == 0:
                match.activate_trading_card(CardId.LAWYER)
                print("Lawyer: turn ended without scoring.")
            elif player.inventory.has_power(CardId.WRITE_OFF):
                match.cast_power_card(CardId.WRITE_OFF)
                print("Write off: turn ended without scoring.")
            else:
                raise WrongPhaseError(
                    "Need Lawyer (ready) or Write off to end without scoring"
                )
        elif command in {"quit", "exit", "q"}:
            return False
        else:
            print(f"Unknown command: {command}. Type `help`.")
    except (ValueError, WrongPhaseError) as exc:
        print(f"Cannot do that: {exc}")
    except Exception as exc:
        print(f"Error: {exc}")

    if match.is_over():
        winner = match.winner()
        print(f"\nMatch over! Winner: {winner.name if winner else 'nobody'}")
        return False
    return True


def run_sandbox(player_names: list[str], starting_chips: int = SANDBOX_STARTING_CHIPS) -> None:
    match = Match(player_names, config=MatchConfig(max_rotations=5))
    for player in match.players:
        player.chips = starting_chips
    match._publish_turn_preview(match.active_player)

    print("Loaded Dice — CLI sandbox")
    print(f"Players: {', '.join(player_names)}")
    _print_help()

    while True:
        _print_status(match)
        if match.phase == TurnPhase.BETWEEN_TURNS and not match.is_over():
            print("\nType `start` to begin the next turn, or `shop` / `buy` / `reroll`.")
            print("Block queued hindrances anytime with `block <index>` before they resolve.")
        elif match.phase == TurnPhase.TURN_START:
            print("\nHindrances queued — `block <index>` then `start` to roll.")
        elif match.phase == TurnPhase.TURN_ACTIVE:
            print("\n`roll`, `lock`, `cast`, `hindrance`, `preview`, `score`, or `end`.")

        try:
            line = input(f"\n[{match.active_player.name}]> ")
        except (EOFError, KeyboardInterrupt):
            print("\nBye.")
            break
        if not _handle_command(match, line):
            break


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Play Loaded Dice in the terminal.")
    parser.add_argument(
        "players",
        nargs="*",
        default=["Alice", "Bob"],
        help="Player names (default: Alice Bob)",
    )
    parser.add_argument(
        "--chips",
        type=int,
        default=SANDBOX_STARTING_CHIPS,
        help=f"Starting chips per player (default: {SANDBOX_STARTING_CHIPS})",
    )
    args = parser.parse_args(argv)
    if len(args.players) < 1:
        parser.error("At least one player name is required")
    run_sandbox(args.players, starting_chips=args.chips)


if __name__ == "__main__":
    main(sys.argv[1:])

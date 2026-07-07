"""Headless match state — wires dice, scoring, and turn order together."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

from loaded_dice.dice import DEFAULT_MAX_ROLLS_PER_TURN, DiceSet, TooManyRollsError
from loaded_dice.economy import (
    CHIPS_PER_SCORED_HAND,
    calculate_compensation,
    calculate_interest,
    chips_for_unused_standard_rolls,
    InsufficientChipsError,
)
from loaded_dice.cards import (
    CardId,
    CardInventory,
    CardNotInInventoryError,
    NEGATIVE_POWER_IDS,
    POSITIVE_POWERS_REQUIRING_TARGET,
)
from loaded_dice.card_effects.negative_power import (
    HindranceConflictError,
    resolve_hindrance,
    validate_hindrance_queue,
)
from loaded_dice.card_effects.positive_power import POSITIVE_POWER_CAST, cast_positive_power
from loaded_dice.effects import TurnEffects
from loaded_dice.scoring import Category, ScoreSheet
from loaded_dice.shop import Shop, ShopError
from loaded_dice.turn_effects import apply_turn_start_passives, resolve_turn_effects


class TurnPhase(Enum):
    BETWEEN_TURNS = "between_turns"
    TURN_START = "turn_start"  # hindrances shown; resolved before rolling (GDD)
    TURN_ACTIVE = "turn_active"


class MatchOverError(Exception):
    """Raised when an action is attempted after the match has ended."""


class WrongPhaseError(Exception):
    """Raised when an action is not allowed in the current phase."""


class MustRollBeforeScoreError(Exception):
    """Raised when scoring is attempted before the active player has rolled."""


class InvalidDieSelectionError(Exception):
    """Raised when die indices for scoring are invalid."""


@dataclass(frozen=True)
class QueuedHindrance:
    """Hindrance waiting to resolve on the target's next turn start."""

    card_id: CardId
    caster_name: str


@dataclass
class RotationAttackRecord:
    """Attack activity for one rotation — used for compensation and card checks."""

    attackers: set[str] = field(default_factory=set)
    attacks_on: dict[str, set[str]] = field(default_factory=dict)

    def record(self, caster_name: str, target_name: str) -> None:
        self.attackers.add(caster_name)
        self.attacks_on.setdefault(target_name, set()).add(caster_name)

    def attacker_count_on(self, player_name: str) -> int:
        return len(self.attacks_on.get(player_name, set()))

    def player_attacked(self, player_name: str) -> bool:
        return player_name in self.attackers


@dataclass
class MatchConfig:
    """Rules for how a match starts and ends. Expand for modes (elimination, etc.)."""

    max_rotations: int | None = None
    refresh_sheet_on_complete: bool = False
    dice_size: int = 5
    max_rolls_per_turn: int = DEFAULT_MAX_ROLLS_PER_TURN


@dataclass
class Player:
    name: str
    current_sheet: ScoreSheet = field(default_factory=ScoreSheet)
    game_total: int = 0
    sheets_completed: int = 0
    chips: int = 0
    inventory: CardInventory = field(default_factory=CardInventory)
    turn_effects: TurnEffects = field(default_factory=TurnEffects)
    queued_hindrances: list[QueuedHindrance] = field(default_factory=list)
    parry_ready: bool = False

    def total_score(self) -> int:
        return self.game_total + self.current_sheet.grand_total()

    def is_out_of_match(self, config: MatchConfig) -> bool:
        if config.refresh_sheet_on_complete:
            return False
        return self.current_sheet.is_complete()

    def earn_chips(self, amount: int) -> None:
        if amount < 0:
            raise ValueError("Cannot earn a negative chip amount")
        self.chips += amount

    def spend_chips(self, amount: int) -> None:
        if amount < 0:
            raise ValueError("Cannot spend a negative chip amount")
        if amount > self.chips:
            raise InsufficientChipsError(
                f"Need {amount} chips but only have {self.chips}"
            )
        self.chips -= amount

    def lose_chips(self, amount: int) -> None:
        if amount < 0:
            raise ValueError("Cannot lose a negative chip amount")
        self.chips = max(0, self.chips - amount)


class Match:
    """Orchestrates players, turns, dice, and scoring for a headless game."""

    def __init__(self, player_names: list[str], config: MatchConfig | None = None) -> None:
        if not player_names:
            raise ValueError("At least one player is required")
        self.config = config or MatchConfig()
        self.players = [Player(name=name) for name in player_names]
        self.phase = TurnPhase.BETWEEN_TURNS
        self._current_index = 0
        self._dice: DiceSet | None = None
        self._rotation_count = 0
        self._current_rotation_attacks = RotationAttackRecord()
        self._previous_rotation_attacks = RotationAttackRecord()
        self.shop = Shop()

    @property
    def active_player(self) -> Player:
        return self.players[self._current_index]

    @property
    def dice(self) -> DiceSet | None:
        return self._dice

    @property
    def rotation_count(self) -> int:
        return self._rotation_count

    def is_over(self) -> bool:
        if self.config.max_rotations is not None:
            return self._rotation_count >= self.config.max_rotations
        return all(player.is_out_of_match(self.config) for player in self.players)

    def start_turn(self) -> None:
        """Begin the active player's turn (GDD: show hindrances in TURN_START)."""
        self._ensure_not_over()
        if self.phase != TurnPhase.BETWEEN_TURNS:
            raise WrongPhaseError(f"Cannot start turn during {self.phase.value}")
        if self.active_player.is_out_of_match(self.config):
            raise WrongPhaseError(f"{self.active_player.name} has finished the match")

        interest = calculate_interest(self.active_player.chips)
        self.active_player.earn_chips(interest)
        if self._rotation_count > 0:
            compensation = calculate_compensation(
                self._previous_rotation_attacks.attacker_count_on(self.active_player.name),
                self._previous_rotation_attacks.player_attacked(self.active_player.name),
            )
            self.active_player.earn_chips(compensation)
        self.active_player.turn_effects = resolve_turn_effects(self.active_player)
        apply_turn_start_passives(self.active_player, self)

        self.phase = TurnPhase.TURN_START
        self._dice = DiceSet(
            size=self.config.dice_size,
            max_rolls=self.config.max_rolls_per_turn,
        )

    def begin_rolling(self) -> None:
        """Move from TURN_START to TURN_ACTIVE (GDD: Start Turn button pressed)."""
        self._ensure_not_over()
        if self.phase != TurnPhase.TURN_START:
            raise WrongPhaseError(f"Cannot begin rolling during {self.phase.value}")
        self._resolve_queued_hindrances(self.active_player)
        self.active_player.parry_ready = False
        self.phase = TurnPhase.TURN_ACTIVE

    def block_hindrance(self, hindrance_index: int) -> None:
        """Cancel one queued hindrance during TURN_START (Parry, Guardian, etc.)."""
        self._ensure_not_over()
        if self.phase != TurnPhase.TURN_START:
            raise WrongPhaseError(f"Cannot block hindrances during {self.phase.value}")

        player = self.active_player
        if hindrance_index < 0 or hindrance_index >= len(player.queued_hindrances):
            raise ValueError(f"Invalid hindrance index: {hindrance_index}")

        if player.parry_ready:
            player.parry_ready = False
        elif player.inventory.has_power(CardId.PARRY):
            player.inventory.consume_power_by_id(CardId.PARRY)
        else:
            raise WrongPhaseError("No parry available")

        player.queued_hindrances.pop(hindrance_index)

    def roll(self) -> list[int]:
        self._ensure_not_over()
        if self.phase != TurnPhase.TURN_ACTIVE:
            raise WrongPhaseError(f"Cannot roll during {self.phase.value}")
        if self._dice is None:
            raise WrongPhaseError("No dice set for this turn")
        return self._dice.roll()

    def lock(self, index: int) -> None:
        self._require_active_dice()
        self._dice.lock(index)

    def unlock(self, index: int) -> None:
        self._require_active_dice()
        self._dice.unlock(index)

    def grant_extra_rolls(self, count: int = 1) -> None:
        """Pass-through for card effects (e.g. The Gambler) on the active turn."""
        self._require_active_dice()
        self._dice.grant_extra_rolls(count)

    def cast_power_card(self, card_id: CardId, **kwargs) -> None:
        """Play a positive power card from the active player's inventory during rolling."""
        self._ensure_not_over()
        if self.phase != TurnPhase.TURN_ACTIVE:
            raise WrongPhaseError(f"Cannot cast power cards during {self.phase.value}")
        if card_id not in POSITIVE_POWER_CAST:
            raise WrongPhaseError(f"{card_id.value} is not a castable positive power card")

        player = self.active_player
        if card_id in POSITIVE_POWERS_REQUIRING_TARGET:
            target = kwargs.get("target")
            if target is None:
                raise ValueError(f"{card_id.value} requires target")
            if target not in self.players:
                raise ValueError("target must be a player in this match")
            if target is player:
                raise ValueError(f"{card_id.value} must target another player")

        try:
            player.inventory.consume_power_by_id(card_id)
        except CardNotInInventoryError as exc:
            raise WrongPhaseError(str(exc)) from exc

        cast_positive_power(card_id, player, self, **kwargs)

    def cast_hindrance(self, card_id: CardId, target: Player) -> None:
        """Queue a negative power card on *target* during the active player's turn."""
        self._ensure_not_over()
        if self.phase != TurnPhase.TURN_ACTIVE:
            raise WrongPhaseError(f"Cannot cast hindrances during {self.phase.value}")
        if card_id not in NEGATIVE_POWER_IDS:
            raise WrongPhaseError(f"{card_id.value} is not a castable hindrance")
        if target not in self.players:
            raise ValueError("target must be a player in this match")
        if target is self.active_player:
            raise ValueError("Cannot cast a hindrance on yourself")

        try:
            validate_hindrance_queue(target, card_id)
        except HindranceConflictError as exc:
            raise WrongPhaseError(str(exc)) from exc

        caster = self.active_player
        try:
            caster.inventory.consume_power_by_id(card_id)
        except CardNotInInventoryError as exc:
            raise WrongPhaseError(str(exc)) from exc

        target.queued_hindrances.append(
            QueuedHindrance(card_id=card_id, caster_name=caster.name)
        )
        self._current_rotation_attacks.record(caster.name, target.name)

    def score(
        self,
        category: Category,
        die_indices: list[int] | None = None,
    ) -> int:
        """Score the current dice into *category* and end the turn."""
        self._ensure_not_over()
        if self.phase != TurnPhase.TURN_ACTIVE:
            raise WrongPhaseError(f"Cannot score during {self.phase.value}")
        if self._dice is None:
            raise WrongPhaseError("No dice set for this turn")
        if self._dice.rolls_this_turn < 1:
            raise MustRollBeforeScoreError("Roll at least once before scoring")

        values = self._select_scoring_values(die_indices)
        points = self.active_player.current_sheet.record(
            values,
            category,
            effects=self.active_player.turn_effects,
        )
        self._award_scoring_income(self.active_player)
        self._on_sheet_completed(self.active_player)
        self._end_turn()
        return points

    def end_turn_without_scoring(self) -> None:
        """End the turn without filling a category (Write off, The Lawyer, etc.)."""
        self._ensure_not_over()
        if self.phase != TurnPhase.TURN_ACTIVE:
            raise WrongPhaseError(f"Cannot end turn during {self.phase.value}")
        self._end_turn()

    def can_use_shop(self, player: Player) -> bool:
        """GDD: shop open between turns for the active player; anytime during others' turns."""
        if self.is_over():
            return False
        if player is self.active_player:
            return self.phase == TurnPhase.BETWEEN_TURNS
        return self.phase in (TurnPhase.BETWEEN_TURNS, TurnPhase.TURN_START, TurnPhase.TURN_ACTIVE)

    def buy_from_shop(self, player: Player, stock_index: int):
        """Buy a card from the shop for *player*."""
        self._ensure_not_over()
        if not self.can_use_shop(player):
            raise WrongPhaseError(f"{player.name} cannot use the shop right now")
        try:
            return self.shop.buy(player, stock_index)
        except ShopError as exc:
            raise WrongPhaseError(str(exc)) from exc

    def reroll_shop(self, player: Player) -> None:
        """Pay to refresh shop stock."""
        self._ensure_not_over()
        if not self.can_use_shop(player):
            raise WrongPhaseError(f"{player.name} cannot use the shop right now")
        try:
            self.shop.reroll_stock(player)
        except InsufficientChipsError as exc:
            raise WrongPhaseError(str(exc)) from exc

    def get_standings(self) -> list[tuple[Player, int]]:
        ranked = sorted(self.players, key=lambda p: p.total_score(), reverse=True)
        return [(player, player.total_score()) for player in ranked]

    def winner(self) -> Player | None:
        if not self.is_over():
            return None
        return self.get_standings()[0][0]

    def player_attacked_last_rotation(self, player: Player) -> bool:
        """Whether *player* cast a hindrance during the previous rotation."""
        return self._previous_rotation_attacks.player_attacked(player.name)

    def attackers_on_player_last_rotation(self, player: Player) -> frozenset[str]:
        """Names of players who attacked *player* during the previous rotation."""
        return frozenset(self._previous_rotation_attacks.attacks_on.get(player.name, set()))

    def player_attacked_player_last_rotation(
        self,
        attacker: Player,
        victim: Player,
    ) -> bool:
        """Whether *attacker* cast a hindrance on *victim* during the previous rotation."""
        return attacker.name in self._previous_rotation_attacks.attacks_on.get(
            victim.name, set()
        )

    def _ensure_not_over(self) -> None:
        if self.is_over():
            raise MatchOverError("Match is already over")

    def _require_active_dice(self) -> None:
        self._ensure_not_over()
        if self.phase != TurnPhase.TURN_ACTIVE:
            raise WrongPhaseError(f"Dice actions are not allowed during {self.phase.value}")
        if self._dice is None:
            raise WrongPhaseError("No dice set for this turn")

    def _select_scoring_values(self, die_indices: list[int] | None) -> list[int]:
        assert self._dice is not None
        all_values = self._dice.values

        if die_indices is None:
            if len(all_values) != 5:
                raise InvalidDieSelectionError(
                    f"Must choose 5 dice when {len(all_values)} are in play"
                )
            return all_values

        if len(die_indices) != 5:
            raise InvalidDieSelectionError("Exactly 5 die indices are required")
        if len(set(die_indices)) != 5:
            raise InvalidDieSelectionError("Die indices must be unique")

        try:
            return [all_values[i] for i in die_indices]
        except IndexError as exc:
            raise InvalidDieSelectionError(f"Invalid die index in {die_indices}") from exc

    def _award_scoring_income(self, player: Player) -> None:
        assert self._dice is not None
        player.earn_chips(CHIPS_PER_SCORED_HAND)
        roll_income = chips_for_unused_standard_rolls(
            self._dice.rolls_this_turn,
            self._dice.standard_max_rolls,
        )
        player.earn_chips(roll_income)

    def _on_sheet_completed(self, player: Player) -> None:
        if not player.current_sheet.is_complete():
            return
        if not self.config.refresh_sheet_on_complete:
            return

        player.game_total += player.current_sheet.grand_total()
        player.sheets_completed += 1
        player.current_sheet = ScoreSheet()

    def _resolve_queued_hindrances(self, player: Player) -> None:
        caster_by_name = {candidate.name: candidate for candidate in self.players}
        for hindrance in player.queued_hindrances:
            caster = caster_by_name.get(hindrance.caster_name)
            if caster is None:
                raise ValueError(f"Unknown caster: {hindrance.caster_name}")
            resolve_hindrance(hindrance.card_id, player, caster, self)
        player.queued_hindrances.clear()

    def _end_turn(self) -> None:
        starting_index = self._current_index
        self._dice = None
        self.phase = TurnPhase.BETWEEN_TURNS

        if self.is_over():
            return

        self._current_index = self._next_player_index()
        if self._current_index <= starting_index:
            self._rotation_count += 1
            self._previous_rotation_attacks = self._current_rotation_attacks
            self._current_rotation_attacks = RotationAttackRecord()

    def _next_player_index(self) -> int:
        count = len(self.players)
        index = self._current_index
        for _ in range(count):
            index = (index + 1) % count
            if not self.players[index].is_out_of_match(self.config):
                return index
        return self._current_index

"""Headless match state — wires dice, scoring, and turn order together."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

from loaded_dice.dice import DEFAULT_MAX_ROLLS_PER_TURN, DiceSet, TooManyRollsError
from loaded_dice.scoring import Category, ScoreSheet


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

    def total_score(self) -> int:
        return self.game_total + self.current_sheet.grand_total()

    def is_out_of_match(self, config: MatchConfig) -> bool:
        if config.refresh_sheet_on_complete:
            return False
        return self.current_sheet.is_complete()


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
        self.phase = TurnPhase.TURN_ACTIVE

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
        points = self.active_player.current_sheet.record(values, category)
        self._on_sheet_completed(self.active_player)
        self._end_turn()
        return points

    def end_turn_without_scoring(self) -> None:
        """End the turn without filling a category (Write off, The Lawyer, etc.)."""
        self._ensure_not_over()
        if self.phase != TurnPhase.TURN_ACTIVE:
            raise WrongPhaseError(f"Cannot end turn during {self.phase.value}")
        self._end_turn()

    def get_standings(self) -> list[tuple[Player, int]]:
        ranked = sorted(self.players, key=lambda p: p.total_score(), reverse=True)
        return [(player, player.total_score()) for player in ranked]

    def winner(self) -> Player | None:
        if not self.is_over():
            return None
        return self.get_standings()[0][0]

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

    def _on_sheet_completed(self, player: Player) -> None:
        if not player.current_sheet.is_complete():
            return
        if not self.config.refresh_sheet_on_complete:
            return

        player.game_total += player.current_sheet.grand_total()
        player.sheets_completed += 1
        player.current_sheet = ScoreSheet()

    def _end_turn(self) -> None:
        starting_index = self._current_index
        self._dice = None
        self.phase = TurnPhase.BETWEEN_TURNS

        if self.is_over():
            return

        self._current_index = self._next_player_index()
        if self._current_index <= starting_index:
            self._rotation_count += 1

    def _next_player_index(self) -> int:
        count = len(self.players)
        index = self._current_index
        for _ in range(count):
            index = (index + 1) % count
            if not self.players[index].is_out_of_match(self.config):
                return index
        return self._current_index

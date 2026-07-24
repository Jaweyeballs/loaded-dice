"""Headless match state — wires dice, scoring, and turn order together."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
import random

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
    UNTARGETED_HINDRANCE_IDS,
)
from loaded_dice.card_effects.negative_power import (
    HindranceConflictError,
    resolve_hindrance,
    try_resolve_hindrance_at_start_turn,
    validate_hindrance_queue,
)
from loaded_dice.card_effects.positive_power import (
    compute_do_over_points,
    POSITIVE_POWER_CAST,
    cast_positive_power,
    try_apply_reinforcements_on_score,
)
from loaded_dice.card_effects.trading import (
    ACTIVATABLE_TRADING_IDS,
    GAMBLER_BASE_COST,
    GAMBLER_COST_STEP,
    GUARDIAN_COOLDOWN_TURNS,
    LAWYER_COOLDOWN_TURNS,
    PSYCHIC_DIE_COUNT,
    TODDLER_DIE_COUNT,
    gecko_compensation_bonus,
)
from loaded_dice.effects import TurnEffects
from loaded_dice.scoring import Category, ScoreSheet, is_yahtzee
from loaded_dice.shop import Shop, ShopError, sell_price_for_card
from loaded_dice.turn_effects import apply_turn_start_passives, resolve_turn_effects


class TurnPhase(Enum):
    BETWEEN_TURNS = "between_turns"
    TURN_START = "turn_start"  # legacy; start_turn now goes straight to TURN_ACTIVE
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


@dataclass(frozen=True)
class HindranceFeedEntry:
    """Killfeed row: a hindrance cast (or blocked) during the match."""

    card_id: CardId
    caster_name: str
    target_name: str
    rotation: int
    blocked: bool = False
    blocker_card_id: CardId | None = None


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
    gambler_next_cost: int = GAMBLER_BASE_COST
    lawyer_cooldown_turns: int = 0
    guardian_cooldown_turns: int = 0
    last_scored_values: list[int] | None = None
    last_scored_category: Category | None = None
    # Positive punishment armed at start turn; applied on the next scored hand.
    pending_score_penalty: int = 0
    jail_locked_index: int | None = None

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

    def lose_points(self, amount: int) -> None:
        """Subtract points from the run total (Blue Shell, etc.)."""
        if amount < 0:
            raise ValueError("Cannot lose a negative point amount")
        self.game_total -= amount


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
        # Leaderboard HUD: freeze placement + score baselines until rotation ends.
        self._score_at_rotation_start = {p.name: p.total_score() for p in self.players}
        self._leaderboard_order = self._ranked_player_names()
        # Psychic: die_index → previewed face for the active turn (viewer HUD).
        self._psychic_previews: dict[int, int] = {}
        self._toddler_used_this_turn = False
        self._psychic_used_this_turn = False
        # Cast/block history for the left-panel killfeed (newest last).
        self.hindrance_feed: list[HindranceFeedEntry] = []

    @property
    def psychic_previews(self) -> dict[int, int]:
        """Psychic ghosts for the HUD, including Twins mirror from source → follower."""
        previews = dict(self._psychic_previews)
        if self._dice is None:
            return previews
        for follower, leader in self._dice.twins_links.items():
            if leader in self._psychic_previews:
                previews[follower] = self._psychic_previews[leader]
        return previews

    @property
    def twins_links(self) -> dict[int, int]:
        if self._dice is None:
            return {}
        return self._dice.twins_links

    @property
    def toddler_used_this_turn(self) -> bool:
        return self._toddler_used_this_turn

    @property
    def psychic_used_this_turn(self) -> bool:
        return self._psychic_used_this_turn

    @property
    def active_player(self) -> Player:
        return self.players[self._current_index]

    @property
    def dice(self) -> DiceSet | None:
        return self._dice

    @property
    def rotation_count(self) -> int:
        return self._rotation_count

    @property
    def leaderboard_order(self) -> list[str]:
        """Placement order frozen at the start of the current rotation."""
        return list(self._leaderboard_order)

    def score_delta_this_rotation(self, player: Player) -> int:
        """Net scoresheet points gained since this rotation began."""
        baseline = self._score_at_rotation_start.get(player.name, 0)
        return player.total_score() - baseline

    def is_over(self) -> bool:
        if self.config.max_rotations is not None:
            return self._rotation_count >= self.config.max_rotations
        return all(player.is_out_of_match(self.config) for player in self.players)

    def start_turn(self) -> None:
        """Begin the active player's turn; resolve remaining queued hindrances."""
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
            compensation += gecko_compensation_bonus(self.active_player)
            self.active_player.earn_chips(compensation)
        self.active_player.turn_effects = resolve_turn_effects(self.active_player)
        apply_turn_start_passives(self.active_player, self)

        self._dice = DiceSet(
            size=self.config.dice_size,
            max_rolls=self.config.max_rolls_per_turn,
        )
        self._toddler_used_this_turn = False
        self._psychic_used_this_turn = False
        self._psychic_previews = {}
        self._resolve_queued_hindrances(self.active_player)
        self.active_player.parry_ready = False
        self.phase = TurnPhase.TURN_ACTIVE

    def begin_rolling(self) -> None:
        """No-op compatibility: Start turn already enters TURN_ACTIVE."""
        self._ensure_not_over()
        if self.phase == TurnPhase.TURN_ACTIVE:
            return
        if self.phase != TurnPhase.TURN_START:
            raise WrongPhaseError(f"Cannot begin rolling during {self.phase.value}")
        self._resolve_queued_hindrances(self.active_player)
        self.active_player.parry_ready = False
        self.phase = TurnPhase.TURN_ACTIVE

    def block_hindrance(
        self,
        hindrance_index: int,
        blocker_card_id: CardId | None = None,
        *,
        player: Player | None = None,
    ) -> None:
        """Cancel one of *player*'s unresolved queued hindrances (Parry, Guardian)."""
        self._ensure_not_over()
        target = player if player is not None else self.active_player
        if hindrance_index < 0 or hindrance_index >= len(target.queued_hindrances):
            raise ValueError(f"Invalid hindrance index: {hindrance_index}")

        used = self._consume_block_card(target, blocker_card_id)
        blocked = target.queued_hindrances.pop(hindrance_index)
        self._append_hindrance_feed(
            card_id=blocked.card_id,
            caster_name=blocked.caster_name,
            target_name=target.name,
            blocked=True,
            blocker_card_id=used,
        )

    def _consume_block_card(
        self,
        player: Player,
        blocker_card_id: CardId | None,
    ) -> CardId:
        """Spend Parry/Guardian (or auto-pick) and return which card was used."""
        if blocker_card_id is None:
            if player.parry_ready:
                player.parry_ready = False
                return CardId.PARRY
            if player.inventory.has_power(CardId.PARRY):
                player.inventory.consume_power_by_id(CardId.PARRY)
                return CardId.PARRY
            if (
                player.inventory.has_trading(CardId.GUARDIAN)
                and player.guardian_cooldown_turns == 0
            ):
                player.guardian_cooldown_turns = GUARDIAN_COOLDOWN_TURNS
                return CardId.GUARDIAN
            raise WrongPhaseError("No parry available")

        if blocker_card_id == CardId.PARRY:
            if player.parry_ready:
                player.parry_ready = False
                return CardId.PARRY
            if player.inventory.has_power(CardId.PARRY):
                player.inventory.consume_power_by_id(CardId.PARRY)
                return CardId.PARRY
            raise WrongPhaseError("No Parry available")

        if blocker_card_id == CardId.GUARDIAN:
            if (
                player.inventory.has_trading(CardId.GUARDIAN)
                and player.guardian_cooldown_turns == 0
            ):
                player.guardian_cooldown_turns = GUARDIAN_COOLDOWN_TURNS
                return CardId.GUARDIAN
            raise WrongPhaseError("Guardian unavailable")

        raise WrongPhaseError(f"{blocker_card_id.value} cannot block a hindrance")

    def _append_hindrance_feed(
        self,
        *,
        card_id: CardId,
        caster_name: str,
        target_name: str,
        blocked: bool = False,
        blocker_card_id: CardId | None = None,
    ) -> None:
        self.hindrance_feed.append(
            HindranceFeedEntry(
                card_id=card_id,
                caster_name=caster_name,
                target_name=target_name,
                rotation=self._rotation_count,
                blocked=blocked,
                blocker_card_id=blocker_card_id,
            )
        )
        # Keep the killfeed bounded for long matches.
        if len(self.hindrance_feed) > 40:
            self.hindrance_feed = self.hindrance_feed[-40:]

    def roll(self) -> list[int]:
        self._ensure_not_over()
        if self.phase != TurnPhase.TURN_ACTIVE:
            raise WrongPhaseError(f"Cannot roll during {self.phase.value}")
        if self._dice is None:
            raise WrongPhaseError("No dice set for this turn")
        if all(die.locked for die in self._dice.dice):
            raise WrongPhaseError("All dice are locked")
        had_twins = bool(self._dice.twins_links)
        values = self._dice.roll()
        # Drop Psychic ghosts for dice that no longer have a pending forced face.
        self._psychic_previews = {
            index: face
            for index, face in self._psychic_previews.items()
            if index in self._dice.forced_next_values
        }
        if had_twins:
            self._consume_twins_card()
        return values

    def lock(self, index: int) -> None:
        self._require_active_dice()
        assert self._dice is not None
        if self._dice.rolls_this_turn < 1:
            return
        player = self.active_player
        self._dice.lock(index)
        if player.jail_locked_index is None:
            if self._consume_queued_hindrance(player, CardId.ALREADY_IN_JAIL):
                player.jail_locked_index = index

    def unlock(self, index: int) -> None:
        self._require_active_dice()
        assert self._dice is not None
        player = self.active_player
        if player.jail_locked_index == index:
            raise WrongPhaseError("Already in jail: that die cannot be unlocked")
        self._dice.unlock(index)

    def grant_extra_rolls(self, count: int = 1) -> None:
        """Pass-through for card effects (e.g. The Gambler) on the active turn."""
        self._require_active_dice()
        self._dice.grant_extra_rolls(count)

    def activate_trading_card(
        self,
        card_id: CardId,
        *,
        die_indices: list[int] | None = None,
    ) -> None:
        """Use an activatable trading card from the active player's party (stays in inventory)."""
        self._ensure_not_over()
        if self.phase != TurnPhase.TURN_ACTIVE:
            raise WrongPhaseError(
                f"Cannot activate trading cards during {self.phase.value}"
            )
        if card_id not in ACTIVATABLE_TRADING_IDS:
            raise WrongPhaseError(f"{card_id.value} is not an activatable trading card")

        player = self.active_player
        if not player.inventory.has_trading(card_id):
            raise CardNotInInventoryError(f"No {card_id.value} in trading inventory")

        if card_id == CardId.GAMBLER:
            self._require_active_dice()
            try:
                player.spend_chips(player.gambler_next_cost)
            except InsufficientChipsError as exc:
                raise WrongPhaseError(str(exc)) from exc
            self.grant_extra_rolls(1)
            player.gambler_next_cost += GAMBLER_COST_STEP
            return

        if card_id == CardId.LAWYER:
            if player.lawyer_cooldown_turns > 0:
                raise WrongPhaseError(
                    f"Lawyer on cooldown ({player.lawyer_cooldown_turns} turns left)"
                )
            self.end_turn_without_scoring()
            # Set after end so this turn's cooldown tick does not consume the fresh CD.
            player.lawyer_cooldown_turns = LAWYER_COOLDOWN_TURNS
            return

        if card_id == CardId.TODDLER:
            self._activate_toddler(die_indices)
            return

        if card_id == CardId.PSYCHIC:
            self._activate_psychic(die_indices)
            return

        raise WrongPhaseError(f"Unhandled trading activation: {card_id.value}")

    def _require_die_indices(self, die_indices: list[int] | None, count: int) -> list[int]:
        self._require_active_dice()
        assert self._dice is not None
        if die_indices is None or len(die_indices) != count:
            raise ValueError(f"Exactly {count} die indices are required")
        if len(set(die_indices)) != count:
            raise ValueError("Die indices must be unique")
        size = len(self._dice.dice)
        for index in die_indices:
            if index < 0 or index >= size:
                raise ValueError(f"Invalid die index: {index}")
        return list(die_indices)

    def _activate_toddler(self, die_indices: list[int] | None) -> None:
        """Immediately roll the two chosen dice (once per turn)."""
        if self._toddler_used_this_turn:
            raise WrongPhaseError("Toddler can only be used once per turn")
        chosen = self._require_die_indices(die_indices, TODDLER_DIE_COUNT)
        assert self._dice is not None
        if self._dice.rolls_this_turn < 1:
            raise ValueError("Roll at least once before using Toddler")

        twins = dict(self._dice.twins_links)
        linked = self._dice.linked_twin_indices()
        resolves_twins = bool(linked.intersection(chosen))
        followers = set(twins)

        for index in chosen:
            # Follower copies the source after leaders (and non-linked dice) roll.
            if index in followers and resolves_twins:
                continue
            self._dice.roll_die_now(index)
            self._psychic_previews.pop(index, None)

        if resolves_twins:
            for follower, leader in twins.items():
                face = self._dice.dice[leader].value
                follower_die = self._dice.dice[follower]
                if face in follower_die.faces:
                    follower_die.value = face
                elif follower in chosen:
                    self._dice.roll_die_now(follower)
                self._psychic_previews.pop(follower, None)
                self._psychic_previews.pop(leader, None)
            self._dice.clear_twins()
            self._consume_twins_card()

        self._toddler_used_this_turn = True

    def _activate_psychic(self, die_indices: list[int] | None) -> None:
        """Preview (and lock in) the next rolled face for two dice (once per turn)."""
        if self._psychic_used_this_turn:
            raise WrongPhaseError("Psychic can only be used once per turn")
        chosen = self._require_die_indices(die_indices, PSYCHIC_DIE_COUNT)
        assert self._dice is not None
        if self._dice.rolls_this_turn < 1:
            raise ValueError("Roll at least once before using Psychic")
        previews: dict[int, int] = {}
        for index in chosen:
            die = self._dice.dice[index]
            face = random.choice(die.faces)
            self._dice.queue_forced_roll(index, face)
            previews[index] = face
        self._psychic_previews.update(previews)
        self._psychic_used_this_turn = True

    def _consume_twins_card(self) -> None:
        """Spend one Twins after a link resolves on a roll."""
        try:
            self.active_player.inventory.consume_power_by_id(CardId.TWINS)
        except CardNotInInventoryError:
            # Link can exist only if a card was present when cast; ignore if already gone.
            pass

    def _clear_twins_without_consuming(self) -> None:
        """Cancel an unused Twins link (score / end turn / explicit cancel)."""
        if self._dice is not None:
            self._dice.clear_twins()

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

        # Do over: validate before consume so a second Yahtzee never spends the card.
        if card_id == CardId.DO_OVER:
            die_indices = kwargs.get("die_indices")
            values = self._select_scoring_values(die_indices)
            self._validate_do_over(player, values)

        # Twins: link or cancel without consuming; card is spent when the link resolves.
        if card_id == CardId.TWINS:
            if not player.inventory.has_power(CardId.TWINS):
                raise WrongPhaseError("No twins in your inventory")
            cast_positive_power(card_id, player, self, **kwargs)
            return

        try:
            player.inventory.consume_power_by_id(card_id)
        except CardNotInInventoryError as exc:
            raise WrongPhaseError(str(exc)) from exc

        cast_positive_power(card_id, player, self, **kwargs)

    def cast_hindrance(self, card_id: CardId, target: Player | None = None) -> None:
        """Queue a negative power card (Blue Shell auto-targets current leader)."""
        self._ensure_not_over()
        if self.phase != TurnPhase.TURN_ACTIVE:
            raise WrongPhaseError(f"Cannot cast hindrances during {self.phase.value}")
        if card_id not in NEGATIVE_POWER_IDS:
            raise WrongPhaseError(f"{card_id.value} is not a castable hindrance")

        if card_id in UNTARGETED_HINDRANCE_IDS:
            target = self._leader_player()
        elif target is None:
            raise ValueError(f"{card_id.value} requires target")
        if target not in self.players:
            raise ValueError("target must be a player in this match")
        if target is self.active_player and card_id not in UNTARGETED_HINDRANCE_IDS:
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
        self._append_hindrance_feed(
            card_id=card_id,
            caster_name=caster.name,
            target_name=target.name,
        )

    def _leader_player(self) -> Player:
        """Current first-place player (name tie-break) for Blue Shell."""
        return max(self.players, key=lambda p: (p.total_score(), p.name))

    def select_scoring_values_for_effects(
        self,
        die_indices: list[int] | None = None,
    ) -> list[int]:
        """Expose scoring-hand selection for card effects (Do over)."""
        return self._select_scoring_values(die_indices)

    def _validate_do_over(self, player: Player, values: list[int]) -> Category:
        """Raise if Do over cannot be used; return the category that would be overwritten."""
        if player.last_scored_category is None:
            raise ValueError("Do over requires a previously scored hand")
        category = player.last_scored_category
        if category == Category.YAHTZEE:
            raise ValueError("Do over cannot overwrite a Yahtzee")
        if self._dice is None or self._dice.rolls_this_turn < 1:
            raise ValueError("Do over requires rolled dice")
        # Another Yahtzee after Yahtzee is filled: score normally (bonus/joker), no Do over.
        if is_yahtzee(values) and not player.current_sheet.is_available(Category.YAHTZEE):
            raise ValueError(
                "Do over cannot be used when rolling another Yahtzee after Yahtzee is scored"
            )
        return category

    def apply_do_over(
        self,
        player: Player,
        values: list[int],
        category: Category | None,
    ) -> int:
        """Overwrite last scored category with this hand's score and end the turn."""
        if player is not self.active_player:
            raise WrongPhaseError("Only the active player can use Do over")
        if category is None:
            raise ValueError("Do over requires a previously scored hand")
        self._fold_pending_score_penalty(player)
        points = compute_do_over_points(values, category, player.turn_effects)
        player.current_sheet.overwrite(
            values,
            category,
            effects=player.turn_effects,
            points=points,
        )
        player.last_scored_values = list(values)
        player.last_scored_category = category
        self._clear_scored_turn_modifiers(player)
        self._award_scoring_income(player)
        self._end_turn()
        return points

    def do_over(self, die_indices: list[int] | None = None) -> int:
        """Consume Do over and overwrite the last scored category with this hand."""
        self._ensure_not_over()
        if self.phase != TurnPhase.TURN_ACTIVE:
            raise WrongPhaseError(f"Cannot use Do over during {self.phase.value}")
        player = self.active_player
        if not player.inventory.has_power(CardId.DO_OVER):
            raise WrongPhaseError("Do over is not in your inventory")
        values = self._select_scoring_values(die_indices)
        category = self._validate_do_over(player, values)
        try:
            player.inventory.consume_power_by_id(CardId.DO_OVER)
        except CardNotInInventoryError as exc:
            raise WrongPhaseError(str(exc)) from exc
        return self.apply_do_over(player, values, category)

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
        self._fold_pending_score_penalty(self.active_player)
        try_apply_reinforcements_on_score(self.active_player, self)
        points = self.active_player.current_sheet.record(
            values,
            category,
            effects=self.active_player.turn_effects,
        )
        self.active_player.last_scored_values = list(values)
        self.active_player.last_scored_category = category
        self._clear_scored_turn_modifiers(self.active_player)
        self._award_scoring_income(self.active_player)
        self._on_sheet_completed(self.active_player)
        self._end_turn()
        return points

    def sell_card(self, player: Player, *, kind: str, index: int) -> int:
        """Remove a held card and pay its sell price. Allowed anytime during a match."""
        self._ensure_not_over()
        if kind == "power":
            cards = player.inventory.power_cards
        elif kind == "trading":
            cards = player.inventory.trading_cards
        else:
            raise ValueError(f"Unknown card kind: {kind}")
        if index < 0 or index >= len(cards):
            raise ValueError(f"Invalid {kind} card index: {index}")

        card = cards.pop(index)
        if (
            card.id == CardId.TWINS
            and player is self.active_player
            and self._dice is not None
        ):
            self._clear_twins_without_consuming()
        payout = sell_price_for_card(card)
        player.earn_chips(payout)
        return payout

    def end_turn_without_scoring(self) -> None:
        """End the turn without filling a category (Lawyer / Write off only)."""
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
        """Resolve start-turn hindrances that are ready; leave the rest queued."""
        caster_by_name = {candidate.name: candidate for candidate in self.players}
        remaining: list[QueuedHindrance] = []
        for hindrance in player.queued_hindrances:
            caster = caster_by_name.get(hindrance.caster_name)
            if caster is None:
                raise ValueError(f"Unknown caster: {hindrance.caster_name}")
            if try_resolve_hindrance_at_start_turn(
                hindrance.card_id, player, caster, self
            ):
                continue
            remaining.append(hindrance)
        player.queued_hindrances = remaining

    def _consume_queued_hindrance(self, player: Player, card_id: CardId) -> bool:
        """Resolve and remove the first queued *card_id*. Returns True if one was consumed."""
        caster_by_name = {candidate.name: candidate for candidate in self.players}
        for index, hindrance in enumerate(player.queued_hindrances):
            if hindrance.card_id != card_id:
                continue
            caster = caster_by_name.get(hindrance.caster_name)
            if caster is None:
                raise ValueError(f"Unknown caster: {hindrance.caster_name}")
            resolve_hindrance(card_id, player, caster, self)
            player.queued_hindrances.pop(index)
            return True
        return False

    def _fold_pending_score_penalty(self, player: Player) -> None:
        """Move armed positive-punishment penalty into this hand's turn effects."""
        if player.pending_score_penalty <= 0:
            return
        player.turn_effects.score_penalty += player.pending_score_penalty
        player.pending_score_penalty = 0

    def _clear_scored_turn_modifiers(self, player: Player) -> None:
        """Drop one-shot score HUD modifiers after they have been applied to a hand."""
        hh = player.turn_effects.helping_hand_bonus
        if hh > 0:
            player.turn_effects.helping_hand_bonus = 0
            player.turn_effects.score_bonus = max(0, player.turn_effects.score_bonus - hh)
        player.turn_effects.score_penalty = 0
        player.pending_score_penalty = 0

    def _end_turn(self) -> None:
        starting_index = self._current_index
        finishing = self.players[starting_index]
        if finishing.lawyer_cooldown_turns > 0:
            finishing.lawyer_cooldown_turns -= 1
        if finishing.guardian_cooldown_turns > 0:
            finishing.guardian_cooldown_turns -= 1
        finishing.jail_locked_index = None

        self._dice = None
        self._psychic_previews = {}
        self.phase = TurnPhase.BETWEEN_TURNS

        if self.is_over():
            return

        self._current_index = self._next_player_index()
        if self._current_index <= starting_index:
            self._rotation_count += 1
            self._previous_rotation_attacks = self._current_rotation_attacks
            self._current_rotation_attacks = RotationAttackRecord()
            self._score_at_rotation_start = {
                p.name: p.total_score() for p in self.players
            }
            self._leaderboard_order = self._ranked_player_names()
    def _ranked_player_names(self) -> list[str]:
        return [
            player.name
            for player in sorted(
                self.players,
                key=lambda p: (-p.total_score(), p.name),
            )
        ]

    def _next_player_index(self) -> int:
        count = len(self.players)
        index = self._current_index
        for _ in range(count):
            index = (index + 1) % count
            if not self.players[index].is_out_of_match(self.config):
                return index
        return self._current_index

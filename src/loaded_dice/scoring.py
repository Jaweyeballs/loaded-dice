"""Standard Yahtzee scoring — categories, point calculation, and score sheets.

Scoring is separate from dice rolling: pass in exactly five chosen die values
and a category, get points back. When more dice were rolled (e.g. Benchwarmer,
The Coin), the caller selects which 5 to pass in. ScoreSheet tracks what each
player has filled in.
"""

from __future__ import annotations

from collections import Counter
from enum import Enum


class Category(Enum):
    ONES = "ones"
    TWOS = "twos"
    THREES = "threes"
    FOURS = "fours"
    FIVES = "fives"
    SIXES = "sixes"
    THREE_OF_A_KIND = "three_of_a_kind"
    FOUR_OF_A_KIND = "four_of_a_kind"
    FULL_HOUSE = "full_house"
    SMALL_STRAIGHT = "small_straight"
    LARGE_STRAIGHT = "large_straight"
    YAHTZEE = "yahtzee"
    CHANCE = "chance"


UPPER_CATEGORIES = frozenset(
    {
        Category.ONES,
        Category.TWOS,
        Category.THREES,
        Category.FOURS,
        Category.FIVES,
        Category.SIXES,
    }
)

LOWER_CATEGORIES = frozenset(set(Category) - UPPER_CATEGORIES)

_UPPER_FACE = {
    Category.ONES: 1,
    Category.TWOS: 2,
    Category.THREES: 3,
    Category.FOURS: 4,
    Category.FIVES: 5,
    Category.SIXES: 6,
}

_FACE_TO_UPPER = {face: category for category, face in _UPPER_FACE.items()}

UPPER_BONUS_THRESHOLD = 63
UPPER_BONUS_POINTS = 35
YAHTZEE_BONUS_POINTS = 100

MIN_DIE_FACE = 0  # blank faces (e.g. The Coin) use 0
MAX_DIE_FACE = 6


class CategoryAlreadyUsedError(Exception):
    """Raised when a player tries to score in a category they already filled."""


class JokerRuleViolationError(Exception):
    """Raised when a second Yahtzee must be scored in a specific category."""


def is_yahtzee(values: list[int]) -> bool:
    return len(values) == 5 and len(set(values)) == 1


def score_hand(values: list[int], category: Category) -> int:
    """Return points for *values* in *category* (does not consult a score sheet)."""
    if len(values) != 5:
        raise ValueError(f"Expected 5 dice values, got {len(values)}")
    if any(v < MIN_DIE_FACE or v > MAX_DIE_FACE for v in values):
        raise ValueError(f"Die values must be {MIN_DIE_FACE}–{MAX_DIE_FACE}, got {values}")

    counts = Counter(values)

    if category in UPPER_CATEGORIES:
        face = _UPPER_FACE[category]
        return sum(v for v in values if v == face)

    if category == Category.THREE_OF_A_KIND:
        return sum(values) if max(counts.values()) >= 3 else 0

    if category == Category.FOUR_OF_A_KIND:
        return sum(values) if max(counts.values()) >= 4 else 0

    if category == Category.FULL_HOUSE:
        return 25 if sorted(counts.values()) == [2, 3] else 0

    if category == Category.SMALL_STRAIGHT:
        unique = set(values)
        straights = ({1, 2, 3, 4}, {2, 3, 4, 5}, {3, 4, 5, 6})
        return 30 if any(s.issubset(unique) for s in straights) else 0

    if category == Category.LARGE_STRAIGHT:
        unique = set(values)
        return 40 if unique in ({1, 2, 3, 4, 5}, {2, 3, 4, 5, 6}) else 0

    if category == Category.YAHTZEE:
        return 50 if is_yahtzee(values) else 0

    if category == Category.CHANCE:
        return sum(values)

    raise ValueError(f"Unknown category: {category}")


class ScoreSheet:
    """Tracks filled categories and running totals for one player."""

    def __init__(self) -> None:
        self._scores: dict[Category, int | None] = {category: None for category in Category} 
        self.yahtzee_bonuses = 0

    def is_available(self, category: Category) -> bool:
        return self._scores[category] is None

    def get_score(self, category: Category) -> int | None:
        return self._scores[category]

    def record(self, values: list[int], category: Category) -> int:
        """Score *values* into *category*. Returns total points gained this action."""
        if not self.is_available(category):
            raise CategoryAlreadyUsedError(f"{category.value} is already filled")

        bonus = self._apply_yahtzee_bonus(values)
        self._enforce_joker_rule(values, category)

        points = score_hand(values, category)
        self._scores[category] = points
        return points + bonus

    def _yahtzee_scored_fifty(self) -> bool:
        return self._scores[Category.YAHTZEE] == 50

    def _apply_yahtzee_bonus(self, values: list[int]) -> int:
        """Award 100-point bonus for additional Yahtzees after the first fifty."""
        if is_yahtzee(values) and self._yahtzee_scored_fifty():
            self.yahtzee_bonuses += YAHTZEE_BONUS_POINTS
            return YAHTZEE_BONUS_POINTS
        return 0

    def _enforce_joker_rule(self, values: list[int], category: Category) -> None:
        """Second+ Yahtzee must use the matching upper box if it is still open."""
        if not is_yahtzee(values) or not self._yahtzee_scored_fifty():
            return

        required_upper = _FACE_TO_UPPER.get(values[0])
        if required_upper is None:
            return
        if self.is_available(required_upper) and category != required_upper:
            raise JokerRuleViolationError(
                f"Yahtzee joker: must score in {required_upper.value}"
            )

    def upper_subtotal(self) -> int:
        return sum(
            score
            for category, score in self._scores.items()
            if category in UPPER_CATEGORIES and score is not None
        )

    def upper_bonus(self) -> int:
        return UPPER_BONUS_POINTS if self.upper_subtotal() >= UPPER_BONUS_THRESHOLD else 0

    def lower_subtotal(self) -> int:
        return sum(
            score
            for category, score in self._scores.items()
            if category in LOWER_CATEGORIES and score is not None
        )

    def grand_total(self) -> int:
        return (
            self.upper_subtotal()
            + self.upper_bonus()
            + self.lower_subtotal()
            + self.yahtzee_bonuses
        )

    def filled_count(self) -> int:
        return sum(1 for score in self._scores.values() if score is not None)

    def is_complete(self) -> bool:
        return self.filled_count() == len(Category)

"""Live score previews — best achievable score per empty category from current dice."""

from __future__ import annotations

from itertools import combinations

from loaded_dice.scoring import Category, ScoreSheet, score_hand

SCORING_HAND_SIZE = 5


def best_score_hand(dice_values: list[int], category: Category) -> int:
    """Return the best score for *category* by choosing any 5 dice from *dice_values*."""
    values, _ = best_scoring_hand(dice_values, category)
    return score_hand(values, category)


def best_scoring_hand(
    dice_values: list[int],
    category: Category,
) -> tuple[list[int], tuple[int, ...]]:
    """Return the best five values and their indices in *dice_values* for *category*."""
    if len(dice_values) < SCORING_HAND_SIZE:
        raise ValueError(
            f"Need at least {SCORING_HAND_SIZE} dice to preview, got {len(dice_values)}"
        )

    best_values: list[int] | None = None
    best_indices: tuple[int, ...] | None = None
    best_points = -1

    for indices in combinations(range(len(dice_values)), SCORING_HAND_SIZE):
        values = [dice_values[i] for i in indices]
        points = score_hand(values, category)
        if points > best_points:
            best_points = points
            best_values = values
            best_indices = indices

    assert best_values is not None and best_indices is not None
    return best_values, best_indices


def preview_scores(dice_values: list[int], sheet: ScoreSheet) -> dict[Category, int]:
    """Best achievable score for each empty category on *sheet* from current dice."""
    if len(dice_values) < SCORING_HAND_SIZE:
        raise ValueError(
            f"Need at least {SCORING_HAND_SIZE} dice to preview, got {len(dice_values)}"
        )

    return {
        category: best_score_hand(dice_values, category)
        for category in Category
        if sheet.is_available(category)
    }

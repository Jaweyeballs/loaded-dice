import pytest

from loaded_dice.preview import best_score_hand, best_scoring_hand, preview_scores
from loaded_dice.scoring import Category, ScoreSheet, score_hand


def test_preview_with_five_dice_matches_score_hand():
    dice = [1, 1, 2, 3, 4]
    assert best_score_hand(dice, Category.ONES) == score_hand(dice, Category.ONES)
    assert best_score_hand(dice, Category.CHANCE) == 11


def test_preview_picks_best_five_from_six():
    # Four 3s + a 5 + an extra 3 → Yahtzee is possible with five 3s
    dice = [3, 3, 3, 3, 5, 3]
    assert best_score_hand(dice, Category.YAHTZEE) == 50
    assert best_score_hand(dice, Category.FIVES) == 5


def test_best_scoring_hand_returns_indices():
    dice = [3, 3, 3, 3, 5, 3]
    values, indices, points = best_scoring_hand(dice, Category.YAHTZEE)
    assert values == [3, 3, 3, 3, 3]
    assert points == 50
    assert len(indices) == 5
    assert all(dice[i] == 3 for i in indices)


def test_preview_scores_only_empty_categories():
    sheet = ScoreSheet()
    sheet.record([6, 6, 6, 6, 6], Category.SIXES)

    dice = [1, 2, 3, 4, 5]
    previews = preview_scores(dice, sheet)

    assert Category.SIXES not in previews
    assert len(previews) == len(Category) - 1
    assert previews[Category.CHANCE] == 15


def test_preview_requires_at_least_five_dice():
    with pytest.raises(ValueError):
        best_score_hand([1, 2, 3, 4], Category.CHANCE)

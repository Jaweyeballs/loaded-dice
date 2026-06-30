import pytest

from loaded_dice.scoring import (
  Category,
  CategoryAlreadyUsedError,
  JokerRuleViolationError,
  ScoreSheet,
  UPPER_BONUS_POINTS,
  YAHTZEE_BONUS_POINTS,
  is_yahtzee,
  score_hand,
)


# --- score_hand: upper section ---


@pytest.mark.parametrize(
  "values,category,expected",
  [
    ([1, 1, 2, 3, 4], Category.ONES, 2),
    ([2, 2, 2, 3, 4], Category.TWOS, 6),
    ([3, 3, 3, 3, 3], Category.THREES, 15),
    ([4, 5, 6, 1, 2], Category.FOURS, 4),
    ([5, 5, 1, 2, 3], Category.FIVES, 10),
    ([6, 1, 2, 3, 4], Category.SIXES, 6),
  ],
)
def test_upper_section_scoring(values, category, expected):
  assert score_hand(values, category) == expected


# --- score_hand: lower section ---


def test_three_of_a_kind():
  assert score_hand([3, 3, 3, 1, 2], Category.THREE_OF_A_KIND) == 12
  assert score_hand([1, 2, 3, 4, 5], Category.THREE_OF_A_KIND) == 0


def test_four_of_a_kind():
  assert score_hand([4, 4, 4, 4, 1], Category.FOUR_OF_A_KIND) == 17
  assert score_hand([1, 2, 3, 4, 5], Category.FOUR_OF_A_KIND) == 0


def test_full_house():
  assert score_hand([2, 2, 3, 3, 3], Category.FULL_HOUSE) == 25
  assert score_hand([1, 2, 3, 4, 5], Category.FULL_HOUSE) == 0


@pytest.mark.parametrize(
  "values",
  [
    [1, 2, 3, 4, 6],
    [2, 3, 4, 5, 6],
    [3, 1, 4, 2, 5],
  ],
)
def test_small_straight(values):
  assert score_hand(values, Category.SMALL_STRAIGHT) == 30


def test_small_straight_fails_without_four_in_a_row():
    assert score_hand([1, 2, 3, 5, 6], Category.SMALL_STRAIGHT) == 0


@pytest.mark.parametrize(
  "values",
  [
    [1, 2, 3, 4, 5],
    [2, 3, 4, 5, 6],
  ],
)
def test_large_straight(values):
  assert score_hand(values, Category.LARGE_STRAIGHT) == 40


def test_large_straight_fails_on_small_straight_only():
  assert score_hand([1, 2, 3, 4, 6], Category.LARGE_STRAIGHT) == 0


def test_yahtzee():
  assert score_hand([5, 5, 5, 5, 5], Category.YAHTZEE) == 50
  assert score_hand([1, 2, 3, 4, 5], Category.YAHTZEE) == 0


def test_chance():
    assert score_hand([1, 2, 3, 4, 5], Category.CHANCE) == 15


def test_zero_face_values_are_valid():
    assert score_hand([0, 1, 2, 3, 4], Category.CHANCE) == 10
    assert score_hand([0, 0, 0, 1, 2], Category.THREE_OF_A_KIND) == 3
    assert score_hand([0, 0, 0, 0, 0], Category.YAHTZEE) == 50


def test_is_yahtzee():
  assert is_yahtzee([6, 6, 6, 6, 6])
  assert not is_yahtzee([1, 2, 3, 4, 5])


# --- ScoreSheet ---


def test_score_sheet_records_and_totals():
  sheet = ScoreSheet()
  sheet.record([1, 1, 2, 3, 4], Category.ONES)
  sheet.record([2, 2, 2, 3, 4], Category.TWOS)
  assert sheet.get_score(Category.ONES) == 2
  assert sheet.upper_subtotal() == 8
  assert not sheet.is_complete()


def test_cannot_score_same_category_twice():
  sheet = ScoreSheet()
  sheet.record([3, 3, 3, 1, 2], Category.THREES)
  with pytest.raises(CategoryAlreadyUsedError):
    sheet.record([3, 3, 3, 3, 3], Category.THREES)


def test_upper_bonus_at_threshold():
    sheet = ScoreSheet()
    sheet.record([6, 6, 6, 6, 6], Category.SIXES)   # 30
    sheet.record([5, 5, 5, 5, 1], Category.FIVES)     # 20
    sheet.record([4, 4, 4, 1, 2], Category.FOURS)     # 12 → 62
    sheet.record([1, 1, 1, 2, 3], Category.ONES)      # 3  → 65
    assert sheet.upper_subtotal() == 65
    assert sheet.upper_bonus() == UPPER_BONUS_POINTS


def test_yahtzee_bonus_on_second_yahtzee():
  sheet = ScoreSheet()
  sheet.record([4, 4, 4, 4, 4], Category.YAHTZEE)  # 50 in yahtzee box
  gained = sheet.record([4, 4, 4, 4, 4], Category.FOURS)  # joker into fours
  assert gained == 20 + YAHTZEE_BONUS_POINTS
  assert sheet.yahtzee_bonuses == YAHTZEE_BONUS_POINTS


def test_yahtzee_joker_must_use_open_upper_box():
  sheet = ScoreSheet()
  sheet.record([4, 4, 4, 4, 4], Category.YAHTZEE)
  with pytest.raises(JokerRuleViolationError):
    sheet.record([4, 4, 4, 4, 4], Category.CHANCE)

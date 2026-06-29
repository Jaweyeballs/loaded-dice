import random

import pytest

from src.loaded_dice.dice import DiceSet, TooManyRollsError


def test_diceset_has_five_dice_by_default():
    ds = DiceSet()
    assert len(ds.dice) == 5


def test_values_are_always_in_range():
    ds = DiceSet()
    ds.roll()
    assert all(1 <= v <= 6 for v in ds.values)


def test_locked_die_does_not_change_on_reroll():
    ds = DiceSet()
    ds.roll()
    ds.lock(0)
    locked_value = ds.dice[0].value
    ds.roll()
    assert ds.dice[0].value == locked_value


def test_unlocked_dice_can_change_on_reroll():
    # Randomness means this isn't deterministic, so we try a handful of
    # seeds and pass as soon as one of them shows a change.
    changed = False
    for seed in range(20):
        random.seed(seed)
        ds = DiceSet()
        ds.roll()
        first_values = ds.values[:]
        ds.roll()
        if ds.values != first_values:
            changed = True
            break
    assert changed


def test_cannot_roll_more_than_three_times_per_turn():
    ds = DiceSet()
    ds.roll()
    ds.roll()
    ds.roll()
    with pytest.raises(TooManyRollsError):
        ds.roll()


def test_reset_for_new_turn_clears_locks_and_roll_count():
    ds = DiceSet()
    ds.roll()
    ds.lock(0)
    ds.reset_for_new_turn()
    assert ds.rolls_this_turn == 0
    assert all(not die.locked for die in ds.dice)

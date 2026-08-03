import pytest

from loaded_dice.economy import (
    CHIPS_PER_SCORED_HAND,
    CHIPS_PER_UNUSED_STANDARD_ROLL,
    COMPENSATION_CHIPS_PER_ATTACKER,
    COMPENSATION_PACIFIST_CHIPS,
    InsufficientChipsError,
    calculate_compensation,
    calculate_interest,
    chips_for_unused_standard_rolls,
)
from loaded_dice.match import Match
from loaded_dice.scoring import Category


@pytest.mark.parametrize(
    "balance,expected",
    [
        (0, 0),
        (199, 0),
        (200, 50),
        (399, 50),
        (400, 100),
        (799, 150),
        (800, 200),
        (10_000, 200),
    ],
)
def test_calculate_interest(balance, expected):
    assert calculate_interest(balance) == expected


@pytest.mark.parametrize(
    ("attackers_on_player", "player_attacked_anyone", "expected"),
    [
        (0, False, COMPENSATION_PACIFIST_CHIPS),
        (0, True, 0),
        (1, False, COMPENSATION_PACIFIST_CHIPS + COMPENSATION_CHIPS_PER_ATTACKER),
        (2, False, COMPENSATION_PACIFIST_CHIPS + 2 * COMPENSATION_CHIPS_PER_ATTACKER),
        (1, True, COMPENSATION_CHIPS_PER_ATTACKER),
        (3, True, 3 * COMPENSATION_CHIPS_PER_ATTACKER),
    ],
)
def test_calculate_compensation(attackers_on_player, player_attacked_anyone, expected):
    assert (
        calculate_compensation(attackers_on_player, player_attacked_anyone) == expected
    )


@pytest.mark.parametrize(
    "rolls_used,expected",
    [
        (1, 2 * CHIPS_PER_UNUSED_STANDARD_ROLL),
        (3, 0),
        (5, 0),
    ],
)
def test_chips_for_unused_standard_rolls(rolls_used, expected):
    assert chips_for_unused_standard_rolls(rolls_used) == expected


def test_player_spend_chips():
    from loaded_dice.match import Player

    player = Player(name="Alice", chips=500)
    player.spend_chips(200)
    assert player.chips == 300


def test_player_cannot_overspend():
    from loaded_dice.match import Player

    player = Player(name="Alice", chips=100)
    with pytest.raises(InsufficientChipsError):
        player.spend_chips(101)


def test_scoring_awards_hand_and_unused_roll_chips():
    match = Match(["Alice"])
    match.start_turn()
    match.roll()
    match.score(Category.CHANCE)
    # 300 for scoring + 150 * 2 unused standard rolls
    expected = CHIPS_PER_SCORED_HAND + 2 * CHIPS_PER_UNUSED_STANDARD_ROLL
    assert match.players[0].chips == expected
    assert match.players[0].last_score_chip_gain == expected
    assert match.players[0].last_score_chip_gain_version == 1
    assert [
        (line.amount, line.label) for line in match.players[0].last_score_chip_lines
    ] == [
        (CHIPS_PER_SCORED_HAND, "scored hand"),
        (CHIPS_PER_UNUSED_STANDARD_ROLL, "unused roll"),
        (CHIPS_PER_UNUSED_STANDARD_ROLL, "unused roll"),
    ]

def test_interest_paid_at_turn_start():
    match = Match(["Alice"])
    match.players[0].chips = 400
    match.start_turn()
    assert match.players[0].chips == 500  # 400 + 100 interest


def test_extra_rolls_do_not_increase_unused_roll_income():
    match = Match(["Alice"])
    match.start_turn()
    match.grant_extra_rolls(2)
    match.roll()
    match.score(Category.CHANCE)
    # Still 2 unused standard rolls, not 4
    assert match.players[0].chips == CHIPS_PER_SCORED_HAND + 2 * CHIPS_PER_UNUSED_STANDARD_ROLL


def test_end_turn_without_scoring_awards_no_income():
    match = Match(["Alice"])
    match.start_turn()
    match.roll()
    match.end_turn_without_scoring()
    assert match.players[0].chips == 0

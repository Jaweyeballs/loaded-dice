from loaded_dice.sandbox import _parse_card_id, _parse_category, _player_by_token
from loaded_dice.cards import CardId
from loaded_dice.match import Match
from loaded_dice.scoring import Category


def test_parse_category_by_name_and_number():
    assert _parse_category("chance") == Category.CHANCE
    assert _parse_category("1") == Category.ONES


def test_parse_card_id_partial_match():
    assert _parse_card_id("icarus") == CardId.ICARUS


def test_player_by_token_name_or_index():
    match = Match(["Alice", "Bob"])
    assert _player_by_token(match, "bob").name == "Bob"
    assert _player_by_token(match, "2").name == "Bob"

from loaded_dice.cards import Card, CardId, CardKind
from loaded_dice.match import Match
from loaded_dice.state import serialize_match


def test_serialize_match_basic_shape():
    match = Match(["Alice", "Bob"])
    match.players[0].chips = 500
    state = serialize_match(match)
    assert state["phase"] == "between_turns"
    assert state["active_player"] == "Alice"
    assert state["is_over"] is False
    assert len(state["players"]) == 2
    assert state["players"][0]["chips"] == 500
    assert state["dice"] is None
    assert "shop" in state


def test_serialize_includes_dice_after_start():
    match = Match(["Alice", "Bob"])
    match.start_turn()
    match.begin_rolling()
    match.roll()
    state = serialize_match(match)
    assert state["dice"] is not None
    assert len(state["dice"]["values"]) == 5
    assert state["previews"] is not None


def test_serialize_inventory_and_hindrances():
    match = Match(["Alice", "Bob"])
    match.start_turn()
    match.begin_rolling()
    match.roll()
    match.players[0].inventory.add_power(Card(CardId.GLASS_HALF_FULL, CardKind.POWER))
    match.cast_hindrance(CardId.GLASS_HALF_FULL, match.players[1])
    state = serialize_match(match)
    bob = next(p for p in state["players"] if p["name"] == "Bob")
    assert bob["queued_hindrances"][0]["card_id"] == "glass_half_full"
    assert bob["queued_hindrances"][0]["caster_name"] == "Alice"

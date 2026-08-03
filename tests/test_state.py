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
    assert state["players"][0]["score_delta"] == 0
    assert state["players"][0]["upper_subtotal"] == 0
    assert state["players"][0]["upper_bonus"] == 0
    assert state["players"][0]["lower_subtotal"] == 0
    assert state["players"][0]["yahtzee_bonus_count"] == 0
    assert state["players"][0]["sheet_total"] == 0
    assert state["leaderboard_order"] == ["Alice", "Bob"]
    assert state["dice"] is None
    assert "shop" in state


def test_serialize_sheet_bonus_fields():
    from loaded_dice.scoring import Category

    match = Match(["Alice"])
    alice = match.players[0]
    sheet = alice.current_sheet
    for category, points in (
        (Category.ONES, 3),
        (Category.TWOS, 6),
        (Category.THREES, 9),
        (Category.FOURS, 12),
        (Category.FIVES, 15),
        (Category.SIXES, 18),
    ):
        sheet._scores[category] = points
    sheet.yahtzee_bonuses = 200

    state = serialize_match(match)
    player = state["players"][0]
    assert player["upper_subtotal"] == 63
    assert player["upper_bonus"] == 35
    assert player["yahtzee_bonus_count"] == 2
    assert player["sheet_total"] == 63 + 35 + 200


def test_score_delta_and_leaderboard_freeze_mid_rotation():
    match = Match(["Alice", "Bob"])
    # Force Alice ahead without finishing the rotation.
    match.players[0].game_total = 50

    state = serialize_match(match)
    alice = next(p for p in state["players"] if p["name"] == "Alice")
    bob = next(p for p in state["players"] if p["name"] == "Bob")
    assert alice["score_delta"] == 50
    assert bob["score_delta"] == 0
    # Order stays frozen at rotation-start ties (name order), not live standings.
    assert state["leaderboard_order"] == ["Alice", "Bob"]

    # Advance through both turns so the rotation rolls over.
    match.start_turn()
    match.roll()
    match.end_turn_without_scoring()
    match.start_turn()
    match.roll()
    match.end_turn_without_scoring()

    assert match.rotation_count == 1
    state = serialize_match(match)
    assert state["leaderboard_order"] == ["Alice", "Bob"]
    alice = next(p for p in state["players"] if p["name"] == "Alice")
    assert alice["total_score"] == 50
    assert alice["score_delta"] == 0  # baseline reset at rotation boundary


def test_serialize_includes_dice_after_start():
    match = Match(["Alice", "Bob"])
    match.start_turn()
    match.roll()
    state = serialize_match(match)
    assert state["dice"] is not None
    assert len(state["dice"]["values"]) == 5
    assert state["previews"] is not None


def test_serialize_inventory_and_hindrances():
    match = Match(["Alice", "Bob"])
    match.start_turn()
    match.roll()
    match.players[0].inventory.add_power(Card(CardId.GLASS_HALF_FULL, CardKind.POWER))
    match.cast_hindrance(CardId.GLASS_HALF_FULL, match.players[1])
    state = serialize_match(match)
    bob = next(p for p in state["players"] if p["name"] == "Bob")
    assert bob["queued_hindrances"][0]["card_id"] == "glass_half_full"
    assert bob["queued_hindrances"][0]["caster_name"] == "Alice"
    assert state["hindrance_feed"] == [
        {
            "card_id": "glass_half_full",
            "caster_name": "Alice",
            "target_name": "Bob",
            "rotation": 0,
            "blocked": False,
            "blocker_card_id": None,
            "kind": "hindrance",
            "points": None,
            "category": None,
        }
    ]
    alice = next(p for p in state["players"] if p["name"] == "Alice")
    assert alice["attacked_last_rotation"] is False
    assert bob["attacked_by_last_rotation"] == []

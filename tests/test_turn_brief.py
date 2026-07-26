"""Tests for Your turn in preview briefs."""

from loaded_dice.cards import CardId, card_for_id
from loaded_dice.match import Match
from loaded_dice.state import serialize_player


def test_turn_preview_lists_interest_and_merchant():
    match = Match(["Alice"])
    alice = match.players[0]
    alice.chips = 400
    alice.inventory.add_trading(card_for_id(CardId.MERCHANT))
    match.start_turn()
    preview = alice.last_turn_preview
    assert preview is not None
    assert preview.kind == "preview"
    labels = [line.label for line in preview.chips]
    assert labels[0] == "Merchant"
    assert labels[-1].startswith("Interest:")
    assert preview.chips[-1].amount == 100
    assert preview.net_chips == sum(line.amount for line in preview.chips)
    assert preview.net_score == 0


def test_turn_preview_chip_order_and_compensation_breakdown():
    match = Match(["Alice", "Diane", "Edward", "Frank"])
    alice, diane, edward, frank = match.players
    alice.chips = 400
    alice.inventory.add_trading(card_for_id(CardId.MERCHANT))
    frank.inventory.add_power(card_for_id(CardId.HELPING_HAND))
    diane.inventory.add_power(card_for_id(CardId.ALREADY_IN_JAIL))
    edward.inventory.add_power(card_for_id(CardId.ALREADY_IN_JAIL))

    # Rotation 0: Alice start/end, then others attack Alice, Frank gifts chips.
    match.start_turn()
    match.end_turn_without_scoring()
    match.start_turn()  # Diane
    match.roll()
    match.cast_hindrance(CardId.ALREADY_IN_JAIL, alice)
    match.end_turn_without_scoring()
    match.start_turn()  # Edward
    match.roll()
    match.cast_hindrance(CardId.ALREADY_IN_JAIL, alice)
    match.end_turn_without_scoring()
    match.start_turn()  # Frank
    match.roll()
    match.cast_power_card(CardId.HELPING_HAND, choice="points", target=alice)
    match.end_turn_without_scoring()
    # New rotation; Alice's turn. Chips before start: 400 + 400 HH = 800 → interest 200.
    match.start_turn()
    preview = alice.last_turn_preview
    assert preview is not None
    assert [line.label for line in preview.chips] == [
        "Merchant",
        "Helping hand casted by Frank",
        "Compensation: Diane",
        "Compensation: Edward",
        "Compensation: Pacifist",
        "Interest: 50 chips per 200 (Max 200)",
    ]
    assert [line.amount for line in preview.chips] == [200, 400, 100, 100, 200, 200]


def test_turn_preview_lists_remaining_debuffs_and_glass():
    match = Match(["Alice", "Bob"])
    alice, bob = match.players
    bob.inventory.add_power(card_for_id(CardId.ALREADY_IN_JAIL))
    bob.inventory.add_power(card_for_id(CardId.GLASS_HALF_FULL))
    match.start_turn()
    match.end_turn_without_scoring()
    match.start_turn()
    match.roll()
    match.cast_hindrance(CardId.ALREADY_IN_JAIL, alice)
    match.cast_hindrance(CardId.GLASS_HALF_FULL, alice)
    match.end_turn_without_scoring()
    match.start_turn()
    preview = alice.last_turn_preview
    assert preview is not None
    assert any("already in jail" in line.lower() for line in preview.debuffs)
    assert any("glass half full" in line.lower() for line in preview.debuffs)
    assert alice.turn_effects.zero_upper is True


def test_helping_hand_chip_gift_appears_on_target_preview():
    match = Match(["Alice", "Bob"])
    alice, bob = match.players
    alice.inventory.add_power(card_for_id(CardId.HELPING_HAND))
    match.start_turn()
    match.roll()
    match.cast_power_card(CardId.HELPING_HAND, choice="points", target=bob)
    match.end_turn_without_scoring()
    match.start_turn()
    preview = bob.last_turn_preview
    assert preview is not None
    assert any(
        "Helping hand" in line.label and line.amount == 400
        for line in preview.chips
    )


def test_turn_preview_serialized_on_player():
    match = Match(["Alice"])
    match.start_turn()
    payload = serialize_player(match.players[0], match)
    assert payload["last_turn_preview"] is not None
    assert payload["last_turn_preview"]["kind"] == "preview"
    assert "net_chips" in payload["last_turn_preview"]
    assert "last_turn_review" not in payload


def test_turn_preview_score_buffs_include_persuader():
    match = Match(["Alice"])
    alice = match.players[0]
    alice.inventory.add_trading(card_for_id(CardId.PERSUADER))
    match.start_turn()
    preview = alice.last_turn_preview
    assert preview is not None
    assert "+3 points on next scored hand (Persuader)" in preview.buffs
    assert preview.net_score == 3

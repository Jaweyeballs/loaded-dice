"""Forecaster snapshot + opponent card privacy."""

from loaded_dice.cards import CardId, card_for_id
from loaded_dice.rooms import Room


def test_forecaster_snapshot_on_start_turn_only():
    room = Room(code="ABCD", starting_chips=1000)
    room.add_player("Alice")
    room.add_player("Bob")
    room.start_match("Alice")
    assert room.match is not None
    alice = room.match.players[0]
    bob = room.match.players[1]
    alice.inventory.add_trading(card_for_id(CardId.FORECASTER))
    bob.inventory.add_power(card_for_id(CardId.GLASS_HALF_EMPTY))

    # Before Start Turn: no snapshot yet.
    assert alice.forecaster_reveals is None
    room.match.start_turn()
    assert alice.forecaster_reveals == {"Bob": ["glass_half_empty"]}

    alice_view = room.public_state(viewer_name="Alice")
    assert alice_view["match"]["forecaster_reveals"] == {
        "Bob": ["glass_half_empty"],
    }
    bob_view = room.public_state(viewer_name="Bob")
    assert bob_view["match"]["forecaster_reveals"] is None

    # Mid-turn acquisition is not reflected until next Start Turn.
    bob.inventory.add_power(card_for_id(CardId.ALREADY_IN_JAIL))
    assert alice.forecaster_reveals == {"Bob": ["glass_half_empty"]}
    assert room.public_state(viewer_name="Alice")["match"]["forecaster_reveals"] == {
        "Bob": ["glass_half_empty"],
    }

    # After scoring / ending turn, peek stays until Alice's next Start Turn.
    room.match.end_turn_without_scoring()
    assert room.public_state(viewer_name="Alice")["match"]["forecaster_reveals"] == {
        "Bob": ["glass_half_empty"],
    }
    # Used cards drop out of the visible peek immediately.
    bob.inventory.power_cards.clear()
    assert room.public_state(viewer_name="Alice")["match"]["forecaster_reveals"] == {
        "Bob": [],
    }


def test_forecaster_clears_after_sell_on_next_start():
    room = Room(code="WXYZ", starting_chips=1000)
    room.add_player("Alice")
    room.add_player("Bob")
    room.start_match("Alice")
    assert room.match is not None
    alice = room.match.players[0]
    bob = room.match.players[1]
    alice.inventory.add_trading(card_for_id(CardId.FORECASTER))
    bob.inventory.add_power(card_for_id(CardId.BLUE_SHELL))
    room.match.start_turn()
    assert alice.forecaster_reveals == {"Bob": ["blue_shell"]}

    # Sell Forecaster mid-turn — snapshot stays visible until next Start Turn.
    alice.inventory.trading_cards.clear()
    assert alice.forecaster_reveals == {"Bob": ["blue_shell"]}
    assert room.public_state(viewer_name="Alice")["match"]["forecaster_reveals"] == {
        "Bob": ["blue_shell"],
    }
    room.match.end_turn_without_scoring()
    assert room.public_state(viewer_name="Alice")["match"]["forecaster_reveals"] == {
        "Bob": ["blue_shell"],
    }
    room.match.start_turn()  # Bob
    room.match.end_turn_without_scoring()
    room.match.start_turn()  # Alice again — no Forecaster
    assert alice.forecaster_reveals is None
    alice_view = room.public_state(viewer_name="Alice")
    assert alice_view["match"]["forecaster_reveals"] is None


def test_opponent_card_ids_are_redacted_in_public_state():
    room = Room(code="HIDE", starting_chips=1000)
    room.add_player("Alice")
    room.add_player("Bob")
    room.start_match("Alice")
    assert room.match is not None
    bob = room.match.players[1]
    bob.inventory.add_power(card_for_id(CardId.GLASS_HALF_EMPTY))
    bob.inventory.add_trading(card_for_id(CardId.MERCHANT))

    alice_view = room.public_state(viewer_name="Alice")
    bob_entry = next(p for p in alice_view["match"]["players"] if p["name"] == "Bob")
    assert bob_entry["power_cards"] == []
    assert bob_entry["trading_cards"] == []
    assert bob_entry["power_count"] == 1
    assert bob_entry["trading_count"] == 1
    assert bob_entry["card_count"] == 2

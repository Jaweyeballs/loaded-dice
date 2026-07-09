import pytest

from loaded_dice.rooms import RoomError, RoomManager


def test_create_and_join_room():
    manager = RoomManager()
    room = manager.create_room()
    assert len(room.code) == 4
    room.add_player("Alice")
    room.add_player("Bob")
    assert room.host_name == "Alice"
    assert room.seated == ["Alice", "Bob"]


def test_only_host_can_start():
    manager = RoomManager()
    room = manager.create_room()
    room.add_player("Alice")
    room.add_player("Bob")
    with pytest.raises(RoomError, match="Only the host"):
        room.start_match("Bob")
    match = room.start_match("Alice")
    assert match.active_player.name == "Alice"
    assert match.players[0].chips == room.starting_chips


def test_need_two_players_to_start():
    manager = RoomManager()
    room = manager.create_room()
    room.add_player("Alice")
    with pytest.raises(RoomError, match="at least 2"):
        room.start_match("Alice")


def test_duplicate_name_is_reconnect():
    manager = RoomManager()
    room = manager.create_room()
    room.add_player("Alice")
    room.add_player("Alice")  # reconnect — no error, still one seat
    assert room.seated == ["Alice"]


def test_public_state_flags_for_viewer():
    manager = RoomManager()
    room = manager.create_room()
    room.add_player("Alice")
    room.add_player("Bob")
    room.start_match("Alice")
    state = room.public_state(viewer_name="Bob")
    assert state["started"] is True
    assert state["match"]["you_are_active"] is False
    assert state["match"]["you_can_use_shop"] is True
    alice_view = room.public_state(viewer_name="Alice")
    assert alice_view["match"]["you_are_active"] is True

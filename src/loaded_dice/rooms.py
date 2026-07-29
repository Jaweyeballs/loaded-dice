"""In-memory multiplayer rooms."""

from __future__ import annotations

import random
import string
from dataclasses import dataclass, field
from typing import Any

from loaded_dice.match import Match, MatchConfig
from loaded_dice.sandbox import SANDBOX_STARTING_CHIPS
from loaded_dice.state import serialize_match

ROOM_CODE_LENGTH = 4
MAX_PLAYERS = 6


class RoomError(Exception):
    """Raised when a room operation is invalid."""


def _generate_code(existing: set[str]) -> str:
    alphabet = string.ascii_uppercase + string.digits
    for _ in range(50):
        code = "".join(random.choice(alphabet) for _ in range(ROOM_CODE_LENGTH))
        if code not in existing:
            return code
    raise RoomError("Could not allocate a room code")


@dataclass
class Room:
    code: str
    host_name: str | None = None
    seated: list[str] = field(default_factory=list)
    match: Match | None = None
    starting_chips: int = SANDBOX_STARTING_CHIPS
    max_rotations: int = 5

    @property
    def started(self) -> bool:
        return self.match is not None

    def add_player(self, name: str) -> None:
        cleaned = name.strip()
        if not cleaned:
            raise RoomError("Player name is required")
        if cleaned in self.seated:
            # Reconnect / replace socket for an existing seat (refresh, StrictMode).
            return
        if self.started:
            raise RoomError("Match already started — cannot join as a new player")
        if len(self.seated) >= MAX_PLAYERS:
            raise RoomError("Room is full")
        if not self.seated:
            self.host_name = cleaned
        self.seated.append(cleaned)

    def remove_player(self, name: str) -> None:
        if name in self.seated and not self.started:
            self.seated.remove(name)
            if self.host_name == name:
                self.host_name = self.seated[0] if self.seated else None

    def start_match(self, requester: str) -> Match:
        if self.started:
            raise RoomError("Match already started")
        if requester != self.host_name:
            raise RoomError("Only the host can start the match")
        if len(self.seated) < 2:
            raise RoomError("Need at least 2 players to start")
        match = Match(
            list(self.seated),
            config=MatchConfig(max_rotations=self.max_rotations),
        )
        for player in match.players:
            player.chips = self.starting_chips
        self.match = match
        return match

    def public_state(self, viewer_name: str | None = None) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "room_code": self.code,
            "host_name": self.host_name,
            "seated": list(self.seated),
            "started": self.started,
            "viewer": viewer_name,
            "match": None,
        }
        if self.match is not None:
            viewer = next(
                (p for p in self.match.players if p.name == viewer_name),
                None,
            ) if viewer_name else None
            match_state = serialize_match(self.match, viewer=viewer)
            if viewer_name:
                match_state["you_are_active"] = (
                    self.match.active_player.name == viewer_name
                )
                match_state["you_can_use_shop"] = (
                    self.match.can_use_shop(viewer) if viewer else False
                )
                match_state["forecaster_reveals"] = self._forecaster_view_for(viewer)
                # Never leak other players' exact card IDs — only counts + Forecaster snapshot.
                for entry in match_state["players"]:
                    if entry["name"] != viewer_name:
                        entry["power_cards"] = []
                        entry["trading_cards"] = []
            payload["match"] = match_state
        return payload

    def _forecaster_view_for(self, viewer) -> dict[str, list[str]] | None:
        """Turn-start snapshot for *viewer*, dropping cards no longer held.

        Stays visible until their next Start Turn refreshes or clears it — including
        after they score / while spectating — so long as the snapshot exists.
        """
        assert self.match is not None
        if viewer is None or viewer.forecaster_reveals is None:
            return None
        by_name = {player.name: player for player in self.match.players}
        filtered: dict[str, list[str]] = {}
        for name, card_ids in viewer.forecaster_reveals.items():
            other = by_name.get(name)
            if other is None:
                filtered[name] = []
                continue
            held = {card.id.value for card in other.inventory.power_cards}
            filtered[name] = [card_id for card_id in card_ids if card_id in held]
        return filtered


class RoomManager:
    def __init__(self) -> None:
        self._rooms: dict[str, Room] = {}

    def create_room(self, starting_chips: int = SANDBOX_STARTING_CHIPS) -> Room:
        code = _generate_code(set(self._rooms))
        room = Room(code=code, starting_chips=starting_chips)
        self._rooms[code] = room
        return room

    def get(self, code: str) -> Room:
        room = self._rooms.get(code.upper())
        if room is None:
            raise RoomError(f"No room with code {code}")
        return room

    def discard_if_empty(self, code: str) -> None:
        room = self._rooms.get(code.upper())
        if room is not None and not room.seated and not room.started:
            del self._rooms[code.upper()]

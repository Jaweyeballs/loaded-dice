"""FastAPI multiplayer server — rooms + WebSocket sync."""

from __future__ import annotations

import json
from typing import Any, Dict, Optional

from fastapi import Body, FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from loaded_dice.actions import ActionError, apply_action
from loaded_dice.rooms import Room, RoomError, RoomManager
from loaded_dice.sandbox import SANDBOX_STARTING_CHIPS

app = FastAPI(title="Loaded Dice")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

manager = RoomManager()

# room_code -> player_name -> WebSocket
_connections: Dict[str, Dict[str, WebSocket]] = {}


class CreateRoomBody(BaseModel):
    starting_chips: int = Field(default=SANDBOX_STARTING_CHIPS, ge=0)


@app.get("/health")
def health() -> Dict[str, str]:
    return {"status": "ok"}


@app.post("/rooms")
def create_room(body: Optional[CreateRoomBody] = Body(default=None)) -> Dict[str, Any]:
    chips = body.starting_chips if body else SANDBOX_STARTING_CHIPS
    room = manager.create_room(starting_chips=chips)
    return {"room_code": room.code}


async def _broadcast(room: Room) -> None:
    sockets = _connections.get(room.code, {})
    dead: list[str] = []
    for name, ws in sockets.items():
        payload = room.public_state(viewer_name=name)
        try:
            await ws.send_json({"type": "state", "payload": payload})
        except Exception:
            dead.append(name)
    for name in dead:
        sockets.pop(name, None)
        room.remove_player(name)


async def _send_error(ws: WebSocket, message: str) -> None:
    await ws.send_json({"type": "error", "message": message})


@app.websocket("/ws/{room_code}")
async def room_socket(websocket: WebSocket, room_code: str) -> None:
    await websocket.accept()
    player_name: str | None = None
    code = room_code.upper()

    try:
        room = manager.get(code)
    except RoomError as exc:
        await _send_error(websocket, str(exc))
        await websocket.close()
        return

    try:
        while True:
            raw = await websocket.receive_text()
            try:
                message = json.loads(raw)
            except json.JSONDecodeError:
                await _send_error(websocket, "Invalid JSON")
                continue

            msg_type = message.get("type")
            try:
                if msg_type == "join":
                    if player_name is not None:
                        raise RoomError("Already joined on this connection")
                    name = str(message.get("player_name", "")).strip()
                    room.add_player(name)
                    player_name = name
                    sockets = _connections.setdefault(code, {})
                    previous = sockets.get(name)
                    if previous is not None and previous is not websocket:
                        try:
                            await previous.close()
                        except Exception:
                            pass
                    sockets[name] = websocket
                    await websocket.send_json(
                        {"type": "joined", "payload": room.public_state(viewer_name=name)}
                    )
                    await _broadcast(room)

                elif msg_type == "start":
                    if player_name is None:
                        raise RoomError("Join the room first")
                    room.start_match(player_name)
                    await _broadcast(room)

                elif msg_type == "action":
                    if player_name is None:
                        raise RoomError("Join the room first")
                    if room.match is None:
                        raise RoomError("Match has not started")
                    action = message.get("action")
                    if not isinstance(action, dict):
                        raise ActionError("Missing action object")
                    apply_action(room.match, player_name, action)
                    await _broadcast(room)

                elif msg_type == "ping":
                    await websocket.send_json({"type": "pong"})

                else:
                    await _send_error(websocket, f"Unknown message type: {msg_type}")

            except (RoomError, ActionError) as exc:
                await _send_error(websocket, str(exc))

    except WebSocketDisconnect:
        pass
    finally:
        if player_name is not None:
            sockets = _connections.get(code, {})
            # Only clear this seat if we still own the socket (reconnect may have replaced us).
            if sockets.get(player_name) is websocket:
                sockets.pop(player_name, None)
                try:
                    room = manager.get(code)
                    if not room.started:
                        room.remove_player(player_name)
                        await _broadcast(room)
                    manager.discard_if_empty(code)
                except RoomError:
                    pass


def main() -> None:
    import uvicorn

    uvicorn.run("loaded_dice.server:app", host="0.0.0.0", port=8000, reload=True)


if __name__ == "__main__":
    main()

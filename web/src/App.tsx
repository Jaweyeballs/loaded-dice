import { useEffect, useRef, useState } from "react";
import { RoomSocket } from "./api";
import { GameView } from "./GameView";
import { Lobby } from "./Lobby";
import { WaitingRoom } from "./WaitingRoom";
import type { RoomState } from "./types";

export default function App() {
  const [playerName, setPlayerName] = useState<string | null>(null);
  const [roomCode, setRoomCode] = useState<string | null>(null);
  const [room, setRoom] = useState<RoomState | null>(null);
  const [error, setError] = useState<string | null>(null);
  const socketRef = useRef<RoomSocket | null>(null);

  useEffect(() => {
    if (!roomCode || !playerName) return;

    let closedByUs = false;
    const socket = new RoomSocket(roomCode, playerName, {
      onJoined: (state) => {
        setRoom(state);
        setError(null);
      },
      onState: (state) => {
        setRoom(state);
      },
      onError: (message) => setError(message),
      onClose: () => {
        if (!closedByUs) {
          setError((prev) => prev ?? "Disconnected from room");
        }
      },
    });
    socketRef.current = socket;
    socket.connect();

    return () => {
      closedByUs = true;
      socket.close();
      socketRef.current = null;
    };
  }, [roomCode, playerName]);

  function enter(code: string, name: string) {
    setError(null);
    setRoom(null);
    setPlayerName(name);
    setRoomCode(code);
  }

  function leave() {
    socketRef.current?.close();
    socketRef.current = null;
    setRoom(null);
    setRoomCode(null);
    setPlayerName(null);
    setError(null);
  }

  function sendAction(action: Record<string, unknown>) {
    setError(null);
    socketRef.current?.action(action);
  }

  if (!playerName || !roomCode) {
    return (
      <div className="app">
        <Lobby onEnter={enter} />
      </div>
    );
  }

  if (!room) {
    return (
      <div className="app lobby">
        <p className="hint">Connecting to room {roomCode}…</p>
        {error && <p className="error">{error}</p>}
        <button type="button" className="secondary" onClick={leave}>
          Cancel
        </button>
      </div>
    );
  }

  return (
    <div className="app">
      {error && <p className="error banner-error">{error}</p>}
      {!room.started || !room.match ? (
        <WaitingRoom
          room={room}
          playerName={playerName}
          onStart={() => socketRef.current?.start()}
          onLeave={leave}
          onUpdateSettings={(settings) =>
            socketRef.current?.updateSettings(settings)
          }
        />
      ) : (
        <GameView
          room={room}
          playerName={playerName}
          onAction={sendAction}
          onLeave={leave}
        />
      )}
    </div>
  );
}

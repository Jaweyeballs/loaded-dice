import type { RoomState } from "./types";

type Props = {
  room: RoomState;
  playerName: string;
  onStart: () => void;
  onLeave: () => void;
};

export function WaitingRoom({ room, playerName, onStart, onLeave }: Props) {
  const isHost = room.host_name === playerName;

  return (
    <div className="waiting">
      <header>
        <h1>Room {room.room_code}</h1>
        <p>Share this code with friends on other devices.</p>
      </header>

      <div className="panel">
        <h2>Players</h2>
        <ul className="seat-list">
          {room.seated.map((name) => (
            <li key={name}>
              {name}
              {name === room.host_name ? " (host)" : ""}
              {name === playerName ? " — you" : ""}
            </li>
          ))}
        </ul>
        {room.seated.length < 2 && (
          <p className="hint">Waiting for at least one more player…</p>
        )}
      </div>

      <div className="row">
        {isHost ? (
          <button
            type="button"
            onClick={onStart}
            disabled={room.seated.length < 2}
          >
            Start match
          </button>
        ) : (
          <p className="hint">Waiting for {room.host_name} to start…</p>
        )}
        <button type="button" className="secondary" onClick={onLeave}>
          Leave
        </button>
      </div>
    </div>
  );
}

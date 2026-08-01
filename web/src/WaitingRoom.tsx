import { useState } from "react";
import type { RoomState } from "./types";

type Props = {
  room: RoomState;
  playerName: string;
  onStart: () => void;
  onLeave: () => void;
  onUpdateSettings: (settings: { max_rotations: number }) => void;
};

export function WaitingRoom({
  room,
  playerName,
  onStart,
  onLeave,
  onUpdateSettings,
}: Props) {
  const isHost = room.host_name === playerName;
  const [settingsOpen, setSettingsOpen] = useState(false);
  const settings = room.settings;
  const maxRotations = settings?.max_rotations ?? 10;
  const minRot = settings?.min_max_rotations ?? 5;
  const maxRot = settings?.max_max_rotations ?? 25;

  function bumpMaxRotations(delta: number) {
    if (!isHost) return;
    const next = Math.min(maxRot, Math.max(minRot, maxRotations + delta));
    if (next !== maxRotations) {
      onUpdateSettings({ max_rotations: next });
    }
  }

  function setMaxRotationsFromInput(raw: string) {
    if (!isHost) return;
    const parsed = Number.parseInt(raw, 10);
    if (Number.isNaN(parsed)) return;
    const next = Math.min(maxRot, Math.max(minRot, parsed));
    onUpdateSettings({ max_rotations: next });
  }

  return (
    <div className="waiting">
      <header className="waiting-head">
        <div>
          <h1>Room {room.room_code}</h1>
          <p>Share this code with friends on other devices.</p>
        </div>
        <button
          type="button"
          className={`secondary settings-toggle ${settingsOpen ? "open" : ""}`}
          onClick={() => setSettingsOpen((v) => !v)}
          aria-expanded={settingsOpen}
        >
          Settings
        </button>
      </header>

      {settingsOpen && (
        <div className="panel settings-panel">
          <h2>Match settings</h2>
          <p className="hint settings-mode-hint">
            Modes coming later — for now you can set how long the match runs.
          </p>
          <label className="settings-field">
            <span className="settings-label">Max rotations</span>
            <span className="settings-help">
              Match ends after this many full rotations ({minRot}–{maxRot}).
            </span>
            <div className="settings-stepper">
              <button
                type="button"
                className="secondary"
                disabled={!isHost || maxRotations <= minRot}
                onClick={() => bumpMaxRotations(-1)}
                aria-label="Decrease max rotations"
              >
                −
              </button>
              <input
                type="number"
                min={minRot}
                max={maxRot}
                value={maxRotations}
                disabled={!isHost}
                onChange={(e) => setMaxRotationsFromInput(e.target.value)}
              />
              <button
                type="button"
                className="secondary"
                disabled={!isHost || maxRotations >= maxRot}
                onClick={() => bumpMaxRotations(1)}
                aria-label="Increase max rotations"
              >
                +
              </button>
            </div>
          </label>
          {!isHost && (
            <p className="hint">Only the host can change settings.</p>
          )}
        </div>
      )}

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
        <p className="hint settings-summary">
          Max rotations: {maxRotations}
        </p>
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

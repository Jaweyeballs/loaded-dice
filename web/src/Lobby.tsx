import { useState, type FormEvent } from "react";
import { createRoom } from "./api";

type Props = {
  onEnter: (roomCode: string, playerName: string) => void;
};

export function Lobby({ onEnter }: Props) {
  const [name, setName] = useState("");
  const [joinCode, setJoinCode] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function handleCreate(e: FormEvent) {
    e.preventDefault();
    const trimmed = name.trim();
    if (!trimmed) {
      setError("Enter a name");
      return;
    }
    setBusy(true);
    setError(null);
    try {
      const code = await createRoom();
      onEnter(code, trimmed);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not create room");
    } finally {
      setBusy(false);
    }
  }

  function handleJoin(e: FormEvent) {
    e.preventDefault();
    const trimmed = name.trim();
    const code = joinCode.trim().toUpperCase();
    if (!trimmed) {
      setError("Enter a name");
      return;
    }
    if (!code) {
      setError("Enter a room code");
      return;
    }
    onEnter(code, trimmed);
  }

  return (
    <div className="lobby">
      <header className="lobby-brand">
        <h1>Loaded Dice</h1>
        <p>Create a room, share the code, play from different browsers.</p>
      </header>

      <label className="field">
        <span>Your name</span>
        <input
          value={name}
          onChange={(e) => setName(e.target.value)}
          placeholder="Alice"
          maxLength={24}
          autoFocus
        />
      </label>

      <form className="panel" onSubmit={handleCreate}>
        <h2>Host a game</h2>
        <button type="submit" disabled={busy}>
          {busy ? "Creating…" : "Create room"}
        </button>
      </form>

      <form className="panel" onSubmit={handleJoin}>
        <h2>Join a game</h2>
        <label className="field">
          <span>Room code</span>
          <input
            value={joinCode}
            onChange={(e) => setJoinCode(e.target.value.toUpperCase())}
            placeholder="ABCD"
            maxLength={8}
          />
        </label>
        <button type="submit">Join room</button>
      </form>

      {error && <p className="error">{error}</p>}
    </div>
  );
}

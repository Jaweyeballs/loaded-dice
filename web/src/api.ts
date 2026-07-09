import type { RoomState, ServerMessage } from "./types";

const API_BASE = import.meta.env.VITE_API_BASE ?? "";

export async function createRoom(startingChips = 1000): Promise<string> {
  const res = await fetch(`${API_BASE}/rooms`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ starting_chips: startingChips }),
  });
  if (!res.ok) {
    throw new Error(`Failed to create room (${res.status})`);
  }
  const data = (await res.json()) as { room_code: string };
  return data.room_code;
}

function wsUrl(roomCode: string): string {
  if (API_BASE.startsWith("http")) {
    const url = new URL(API_BASE);
    url.protocol = url.protocol === "https:" ? "wss:" : "ws:";
    url.pathname = `/ws/${roomCode}`;
    return url.toString();
  }
  const proto = window.location.protocol === "https:" ? "wss:" : "ws:";
  return `${proto}//${window.location.host}/ws/${roomCode}`;
}

export type RoomSocketHandlers = {
  onJoined: (state: RoomState) => void;
  onState: (state: RoomState) => void;
  onError: (message: string) => void;
  onClose: () => void;
};

export class RoomSocket {
  private ws: WebSocket | null = null;

  constructor(
    private roomCode: string,
    private playerName: string,
    private handlers: RoomSocketHandlers,
  ) {}

  connect(): void {
    this.ws = new WebSocket(wsUrl(this.roomCode));
    this.ws.onopen = () => {
      this.send({ type: "join", player_name: this.playerName });
    };
    this.ws.onmessage = (event) => {
      const msg = JSON.parse(event.data) as ServerMessage;
      if (msg.type === "joined") this.handlers.onJoined(msg.payload);
      else if (msg.type === "state") this.handlers.onState(msg.payload);
      else if (msg.type === "error") this.handlers.onError(msg.message);
    };
    this.ws.onclose = () => this.handlers.onClose();
  }

  start(): void {
    this.send({ type: "start" });
  }

  action(action: Record<string, unknown>): void {
    this.send({ type: "action", action });
  }

  close(): void {
    this.ws?.close();
    this.ws = null;
  }

  private send(payload: Record<string, unknown>): void {
    if (!this.ws || this.ws.readyState !== WebSocket.OPEN) {
      this.handlers.onError("Not connected to room");
      return;
    }
    this.ws.send(JSON.stringify(payload));
  }
}

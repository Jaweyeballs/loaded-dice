export type CardInfo = {
  id: string;
  kind: string;
  transparent: boolean;
};

export type PlayerState = {
  name: string;
  chips: number;
  total_score: number;
  /** Points gained on the scoresheet since this rotation started. */
  score_delta: number;
  game_total: number;
  sheet: Record<string, number | null>;
  power_cards: CardInfo[];
  trading_cards: CardInfo[];
  queued_hindrances: { card_id: string; caster_name: string }[];
  turn_effects: {
    zero_upper: boolean;
    zero_lower: boolean;
    score_bonus: number;
    score_penalty: number;
  };
  parry_ready: boolean;
  can_use_shop: boolean;
};

export type MatchState = {
  phase: string;
  rotation_count: number;
  active_player: string;
  is_over: boolean;
  winner: string | null;
  /** Placement names frozen at rotation start (server authority). */
  leaderboard_order: string[];
  players: PlayerState[];
  dice: {
    values: number[];
    locked: boolean[];
    rolls_this_turn: number;
    max_rolls: number;
  } | null;
  shop: {
    stock: { index: number; card_id: string; price: number }[];
    reroll_cost: number;
  };
  previews: Record<string, number> | null;
  you_are_active?: boolean;
  you_can_use_shop?: boolean;
};

export type RoomState = {
  room_code: string;
  host_name: string | null;
  seated: string[];
  started: boolean;
  viewer: string | null;
  match: MatchState | null;
};

export type ServerMessage =
  | { type: "joined"; payload: RoomState }
  | { type: "state"; payload: RoomState }
  | { type: "error"; message: string }
  | { type: "pong" };

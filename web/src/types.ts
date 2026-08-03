export type CardInfo = {
  id: string;
  kind: string;
  transparent: boolean;
  /** Chips gained if sold from inventory. */
  sell_price?: number;
};

export type PlayerState = {
  name: string;
  chips: number;
  total_score: number;
  /** Points gained on the scoresheet since this rotation started. */
  score_delta: number;
  game_total: number;
  sheet: Record<string, number | null>;
  /** Last category filled by scoring (for Do over). */
  last_scored_category?: string | null;
  /** Chips from the most recent scored hand (base + unused-roll income). */
  last_score_chip_gain?: number | null;
  /** Increments each score so the HUD can replay the same amount. */
  last_score_chip_gain_version?: number;
  /** Per-line HUD flash: scored hand first, then each unused roll. */
  last_score_chip_lines?: { amount: number; label: string }[];
  /** Latest chip spend amount for the red HUD flash. */
  last_chip_spend?: number | null;
  last_chip_spend_version?: number;
  upper_subtotal?: number;
  upper_bonus?: number;
  lower_subtotal?: number;
  /** Number of +100 Yahtzee bonuses earned on this sheet. */
  yahtzee_bonus_count?: number;
  /** Current sheet grand total (upper + bonus + lower + yahtzee bonuses). */
  sheet_total?: number;
  power_cards: CardInfo[];
  trading_cards: CardInfo[];
  /** Public inventory sizes (safe to show for opponents). */
  power_count?: number;
  trading_count?: number;
  card_count?: number;
  /** Held power cards / capacity (transparent cards expand capacity). */
  power_slots_used?: number;
  power_slot_capacity?: number;
  trading_slots_used?: number;
  trading_slot_capacity?: number;
  queued_hindrances: {
    card_id: string;
    caster_name: string;
    /** Caster holds The Mixup — Parry cannot block this. */
    mixup?: boolean;
    /** Effect already applied; still shown for hover until cleared. */
    active?: boolean;
  }[];
  pending_score_penalty?: number;
  /** Signed modifiers shown under the scoresheet (null when none). */
  score_breakdown?: {
    lines: { label: string; amount: number }[];
    net: number;
  } | null;
  turn_effects: {
    zero_upper: boolean;
    zero_lower: boolean;
    score_bonus: number;
    score_penalty: number;
    helping_hand_bonus?: number;
  };
  parry_ready: boolean;
  can_use_shop: boolean;
  gambler_cost: number;
  lawyer_cooldown: number;
  guardian_cooldown: number;
  /** True if this player cast a hindrance last rotation. */
  attacked_last_rotation?: boolean;
  /** True when pacifist rewards apply. */
  pacifist_qualified?: boolean;
  /** Players who cast a hindrance on this player last rotation. */
  attacked_by_last_rotation?: string[];
  /** Latest "your turn in preview" brief (ready before Start Turn). */
  last_turn_preview?: TurnBrief | null;
};

export type TurnBrief = {
  kind: "preview" | string;
  version: number;
  debuffs: string[];
  chips: { amount: number; label: string }[];
  buffs: string[];
  scores: { amount: number; label: string }[];
  net_chips: number;
  net_score: number;
};

export type MatchState = {
  phase: string;
  rotation_count: number;
  /** Match ends when rotation_count reaches this (null = unlimited). */
  max_rotations?: number | null;
  active_player: string;
  is_over: boolean;
  winner: string | null;
  /** Placement names frozen at rotation start (server authority). */
  leaderboard_order: string[];
  players: PlayerState[];
    dice: {
    values: number[];
    locked: boolean[];
    /** Parallel to values — standard | benchwarmer | boolean | … */
    kinds?: string[];
    /** Parallel to values — legal faces for that die (Space Die, etc.). */
    faces?: number[][];
    rolls_this_turn: number;
    max_rolls: number;
    /** Die index locked by Already in Jail this turn, if any. */
    jail_locked_index?: number | null;
    /** Die indices force-locked by Smoke Bomb this turn. */
    smoke_bomb_locked_indices?: number[];
  } | null;
  shop: {
    stock: {
      index: number;
      card_id: string | null;
      price: number | null;
      kind?: string | null;
      sold_out?: boolean;
    }[];
    reroll_cost: number;
    full_catalog?: boolean;
  };
  /** Room playtest mode — full catalog shop, etc. */
  dev_mode?: boolean;
  previews: Record<string, number> | null;
  /** Live overwrite preview when Do over is usable this turn. */
  do_over_preview?: { category: string; points: number } | null;
  psychic_previews?: Record<string, number>;
  /** follower index → source index while Twins is linked. */
  twins_links?: Record<string, number>;
  toddler_used_this_turn?: boolean;
  psychic_used_this_turn?: boolean;
  forecaster_reveals?: Record<string, string[]> | null;
  /** Newest last — hindrance cast/block, power uses, and scores for History. */
  hindrance_feed?: {
    card_id?: string | null;
    caster_name: string;
    target_name: string;
    rotation: number;
    blocked: boolean;
    blocker_card_id?: string | null;
    /** "hindrance" | "power_use" | "score". */
    kind?: string;
    points?: number | null;
    category?: string | null;
  }[];
  you_are_active?: boolean;
  you_can_use_shop?: boolean;
};

export type RoomSettings = {
  max_rotations: number;
  min_max_rotations: number;
  max_max_rotations: number;
  /** Full shop catalog + 9999 starting chips while testing. */
  dev_mode: boolean;
};

export type RoomState = {
  room_code: string;
  host_name: string | null;
  seated: string[];
  started: boolean;
  viewer: string | null;
  settings?: RoomSettings;
  match: MatchState | null;
};

export type ServerMessage =
  | { type: "joined"; payload: RoomState }
  | { type: "state"; payload: RoomState }
  | { type: "error"; message: string }
  | { type: "pong" };

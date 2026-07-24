import { useEffect, useLayoutEffect, useMemo, useRef, useState } from "react";
import { cardBlurb, cardTipLabel } from "./cardCopy";
import { Tip } from "./Tip";
import type { CardInfo, MatchState, PlayerState, RoomState } from "./types";

type Props = {
  room: RoomState;
  playerName: string;
  onAction: (action: Record<string, unknown>) => void;
  onLeave: () => void;
};

type DieScatter = { x: number; y: number; rot: number };

type RollAnim = {
  /** Current tray DOM order (pre-toss, then sorted for the snap-home). */
  order: number[];
  /** Indices that leave the tray. */
  flying: number[];
  scatter: Record<number, DieScatter>;
  /** FLIP invert transforms so dice stay visually on the felt after reorder. */
  hold: Record<number, DieScatter>;
  /** Screen positions measured just before switching to sorted order. */
  firstRects: Record<number, { left: number; top: number }>;
  /** Face shown on each die during the toss (old faces, then new). */
  displayValues: Record<number, number>;
  /** Dice that have finished snapping into the sorted tray. */
  returned: number[];
  phase: "prep" | "out" | "flip" | "back";
  /** Suppress CSS transition only while applying the FLIP invert. */
  freezeMotion: boolean;
};

function randomScatter(): DieScatter {
  const side = Math.random() < 0.5 ? -1 : 1;
  return {
    x: side * (40 + Math.random() * 150) + (Math.random() - 0.5) * 40,
    y: -(55 + Math.random() * 170),
    rot: (Math.random() - 0.5) * 640,
  };
}

/** Scoresheet row order — includes summary rows that are not scoreable categories. */
type SheetRow =
  | { kind: "category"; id: string }
  | { kind: "summary"; id: string };

const SHEET_ROWS: SheetRow[] = [
  { kind: "category", id: "ones" },
  { kind: "category", id: "twos" },
  { kind: "category", id: "threes" },
  { kind: "category", id: "fours" },
  { kind: "category", id: "fives" },
  { kind: "category", id: "sixes" },
  { kind: "summary", id: "bonus" },
  { kind: "summary", id: "top_half_total" },
  { kind: "category", id: "three_of_a_kind" },
  { kind: "category", id: "four_of_a_kind" },
  { kind: "category", id: "full_house" },
  { kind: "category", id: "small_straight" },
  { kind: "category", id: "large_straight" },
  { kind: "category", id: "yahtzee" },
  { kind: "category", id: "chance" },
  { kind: "summary", id: "yahtzee_bonus" },
  { kind: "summary", id: "lower_half_total" },
  { kind: "summary", id: "total" },
];

const CATEGORY_HOVER: Record<string, string> = {
  ones: "count and add only ones",
  twos: "count and add only twos",
  threes: "count and add only threes",
  fours: "count and add only fours",
  fives: "count and add only fives",
  sixes: "count and add only sixes",
  bonus: "if total score is 63 or over; 35 points",
  top_half_total: "total of top half scores",
  three_of_a_kind: "add total of all dice",
  four_of_a_kind: "add total of all dice",
  full_house: "pair and 3 of a kind; 25 points",
  small_straight: "4 in a row; 30 points",
  large_straight: "5 in a row; 40 points",
  yahtzee: "6 if a kind; score 50",
  chance: "add total of all dice",
  yahtzee_bonus: "100 points per extra yahtzee",
  lower_half_total: "total of lower half scores",
  total: "total of all scores",
};

const SUMMARY_LABELS: Record<string, string> = {
  bonus: "bonus",
  top_half_total: "top half total",
  yahtzee_bonus: "yahtzee bonus",
  lower_half_total: "lower half total",
  total: "total",
};

const HINDRANCE_IDS = new Set([
  "glass_half_empty",
  "glass_half_full",
  "positive_punishment",
  "negative_punishment",
  "blue_shell",
  "already_in_jail",
]);

const UNTARGETED_HINDRANCES = new Set(["blue_shell"]);

/** Trading cards clicked to activate (stay in party). Others are passives / turn-start. */
const ACTIVATABLE_TRADING = new Set(["gambler", "lawyer", "toddler", "psychic"]);

const REINFORCEMENT_IDS = new Set([
  "positive_reinforcement",
  "negative_reinforcement",
]);
const PUNISHMENT_IDS = new Set(["positive_punishment", "negative_punishment"]);

type SheetMode = "mine" | "current";
type LeftTab = "history" | "leaderboard";
type DiePickMode =
  | { mode: "trading"; cardId: "toddler" | "psychic"; picked: number[] }
  | { mode: "twins"; picked: number[] }
  | { mode: "score"; category: string; picked: number[] }
  | { mode: "do_over"; picked: number[] };
/** Armed card waiting for a leaderboard click to pick another player. */
type PlayerTargetMode =
  | { kind: "hindrance"; cardId: string; slotIndex: number }
  | { kind: "helping_hand" };

function formatScoreDelta(delta: number): string {
  if (delta > 0) return `+${delta}`;
  if (delta < 0) return `−${Math.abs(delta)}`;
  return "+0";
}

/** Compare frozen place vs live standings; no arrow if placement would stay put. */
function placementArrow(
  name: string,
  displayedPlace: number,
  predictedOrder: string[],
): "up" | "down" | null {
  const predictedPlace = predictedOrder.indexOf(name);
  if (predictedPlace < 0) return null;
  if (predictedPlace < displayedPlace) return "up";
  if (predictedPlace > displayedPlace) return "down";
  return null;
}

function label(id: string): string {
  return id.replace(/_/g, " ");
}

function tipText(cardId: string, transparent = false, extra?: string): string {
  const head = cardTipLabel(cardId, transparent);
  const body = cardBlurb(cardId);
  return extra ? `${head} — ${body} ${extra}` : `${head} — ${body}`;
}

function debuffOnYouTip(cardId: string, casterName: string): string {
  return `${tipText(cardId)}\nCast on you by ${casterName}`;
}

function killfeedLine(entry: {
  card_id: string;
  caster_name: string;
  target_name: string;
  blocked: boolean;
  blocker_card_id?: string | null;
}): string {
  if (entry.blocked) {
    const withCard = entry.blocker_card_id
      ? ` with ${label(entry.blocker_card_id)}`
      : "";
    return `${entry.target_name} has blocked ${entry.caster_name}'s ${label(entry.card_id)}${withCard}`;
  }
  return `${entry.caster_name} → ${entry.target_name}: ${label(entry.card_id)}`;
}

function conditionStatus(
  cardId: string,
  me: PlayerState | undefined,
  rotationCount: number,
): "ACTIVE" | "DORMANT" | null {
  if (REINFORCEMENT_IDS.has(cardId)) {
    if (rotationCount <= 0) return "DORMANT";
    return me?.attacked_last_rotation ? "DORMANT" : "ACTIVE";
  }
  if (PUNISHMENT_IDS.has(cardId)) {
    if (rotationCount <= 0) return "DORMANT";
    return (me?.attacked_by_last_rotation?.length ?? 0) > 0 ? "ACTIVE" : "DORMANT";
  }
  return null;
}

function cooldownTurnsLeft(cardId: string, me: PlayerState | undefined): number {
  if (cardId === "guardian") return me?.guardian_cooldown ?? 0;
  if (cardId === "lawyer") return me?.lawyer_cooldown ?? 0;
  return 0;
}

function CardFace({
  cardId,
  me,
  rotationCount,
  title,
}: {
  cardId: string;
  me: PlayerState | undefined;
  rotationCount: number;
  title?: string;
}) {
  const status = conditionStatus(cardId, me, rotationCount);
  const cd = cooldownTurnsLeft(cardId, me);
  return (
    <>
      {title ?? label(cardId)}
      {status && (
        <span className={`card-status ${status === "ACTIVE" ? "active" : "dormant"}`}>
          {status}
        </span>
      )}
      {cd > 0 && (
        <span className="card-cooldown">
          COOLDOWN: {cd} turn{cd === 1 ? "" : "s"} left
        </span>
      )}
    </>
  );
}


export function GameView({ room, playerName, onAction, onLeave }: Props) {
  const match = room.match as MatchState;
  const me = match.players.find((p) => p.name === playerName);
  const active = Boolean(match.you_are_active);
  const canShop = Boolean(match.you_can_use_shop);

  const [leftOpen, setLeftOpen] = useState(true);
  const [leftTab, setLeftTab] = useState<LeftTab>("leaderboard");
  const [sheetOpen, setSheetOpen] = useState(true);
  const [sheetFullscreen, setSheetFullscreen] = useState(false);
  const [sheetMode, setSheetMode] = useState<SheetMode>("mine");
  const [mineSelection, setMineSelection] = useState(playerName);
  const [cardsOpen, setCardsOpen] = useState(true);
  const [shopOpen, setShopOpen] = useState(false);
  const [icarusArming, setIcarusArming] = useState(false);
  const [spaceArming, setSpaceArming] = useState(false);
  const [spaceFace, setSpaceFace] = useState(6);
  const [helpingChoice, setHelpingChoice] = useState<"chips" | "points">("chips");
  const [diePick, setDiePick] = useState<DiePickMode | null>(null);
  const [blockArming, setBlockArming] = useState<"parry" | "guardian" | null>(null);
  const [playerTarget, setPlayerTarget] = useState<PlayerTargetMode | null>(null);
  const [rollAnim, setRollAnim] = useState<RollAnim | null>(null);
  const prevDiceRef = useRef<{
    rolls: number;
    order: number[];
    locked: boolean[];
    values: number[];
  } | null>(null);
  const rollTimersRef = useRef<number[]>([]);
  const rollRafRef = useRef<number[]>([]);
  const dieElsRef = useRef<Map<number, HTMLButtonElement>>(new Map());
  const flipHandledRef = useRef(false);
  const tossGenRef = useRef(0);
  /** Toddler (and similar): force a toss of specific indices on the next dice update. */
  const pendingTossRef = useRef<{
    flying: number[];
    oldValues: number[];
    trayOrder: number[];
  } | null>(null);

  // Display faces low→high, but keep each die's original index for lock/Icarus actions.
  const sortedDice = useMemo(() => {
    if (!match.dice) return [];
    return match.dice.values
      .map((value, index) => ({
        value,
        index,
        locked: match.dice!.locked[index],
        kind: match.dice!.kinds?.[index] ?? "standard",
      }))
      .sort((a, b) => a.value - b.value || a.index - b.index);
  }, [match.dice]);

  const trayDice = useMemo(() => {
    if (!match.dice) return [];
    if (rollAnim) {
      return rollAnim.order
        .filter((index) => index < match.dice!.values.length)
        .map((index) => ({
          value: rollAnim.displayValues[index] ?? match.dice!.values[index],
          index,
          locked: match.dice!.locked[index],
          kind: match.dice!.kinds?.[index] ?? "standard",
        }));
    }
    return sortedDice;
  }, [match.dice, rollAnim, sortedDice]);

  function clearTossTimers() {
    for (const id of rollTimersRef.current) window.clearTimeout(id);
    rollTimersRef.current = [];
    for (const id of rollRafRef.current) window.cancelAnimationFrame(id);
    rollRafRef.current = [];
  }

  function beginTossAnimation(args: {
    trayOrder: number[];
    flying: number[];
    oldValues: number[];
    newValues: number[];
  }) {
    const { trayOrder, flying, oldValues, newValues } = args;
    if (flying.length === 0) return;

    clearTossTimers();
    flipHandledRef.current = false;
    const gen = ++tossGenRef.current;

    const scatter: Record<number, DieScatter> = {};
    for (const index of flying) scatter[index] = randomScatter();

    const displayValues: Record<number, number> = {};
    for (let i = 0; i < oldValues.length; i++) displayValues[i] = oldValues[i];

    const sortedOrder = [...newValues.keys()].sort(
      (a, b) => newValues[a] - newValues[b] || a - b,
    );

    setRollAnim({
      order: trayOrder,
      flying,
      scatter,
      hold: {},
      firstRects: {},
      displayValues,
      returned: [],
      phase: "prep",
      freezeMotion: false,
    });

    // Next frame: scatter out from the tray with CSS transition.
    const tOut = window.setTimeout(() => {
      if (tossGenRef.current !== gen) return;
      setRollAnim((cur) => (cur ? { ...cur, phase: "out" } : null));
    }, 40);

    // Reveal new faces while dice are on the felt.
    const tReveal = window.setTimeout(() => {
      if (tossGenRef.current !== gen) return;
      const next: Record<number, number> = {};
      for (let i = 0; i < newValues.length; i++) next[i] = newValues[i];
      setRollAnim((cur) => (cur ? { ...cur, displayValues: next } : null));
    }, 320);

    // Reorder tray to sorted slots and FLIP-snap home.
    const tFlip = window.setTimeout(() => {
      if (tossGenRef.current !== gen) return;
      const firstRects: Record<number, { left: number; top: number }> = {};
      for (const index of trayOrder) {
        const el = dieElsRef.current.get(index);
        if (!el) continue;
        const rect = el.getBoundingClientRect();
        firstRects[index] = { left: rect.left, top: rect.top };
      }
      const finalDisplay: Record<number, number> = {};
      for (let i = 0; i < newValues.length; i++) finalDisplay[i] = newValues[i];
      setRollAnim((cur) =>
        cur
          ? {
              ...cur,
              order: sortedOrder,
              firstRects,
              displayValues: finalDisplay,
              hold: {},
              returned: [],
              phase: "flip",
              freezeMotion: true,
            }
          : null,
      );
    }, 720);

    rollTimersRef.current.push(tOut, tReveal, tFlip);
  }

  // Detect a new roll, a pending Toddler toss, or multi-die face change and toss.
  useEffect(() => {
    if (!match.dice) {
      prevDiceRef.current = null;
      pendingTossRef.current = null;
      setRollAnim(null);
      return;
    }

    const rolls = match.dice.rolls_this_turn;
    const order = sortedDice.map((d) => d.index);
    const locked = [...match.dice.locked];
    const values = [...match.dice.values];
    const prev = prevDiceRef.current;
    const pending = pendingTossRef.current;

    // Toddler: treat the picked dice as the only unlocked dice in a roll toss,
    // even when a face lands on the same number (no value delta).
    if (pending) {
      const valuesChanged =
        values.length === pending.oldValues.length &&
        values.some((v, i) => v !== pending.oldValues[i]);
      const toddlerDone = Boolean(match.toddler_used_this_turn);
      if (!valuesChanged && !toddlerDone) {
        // Action in flight — wait for the server state update.
        return;
      }
      pendingTossRef.current = null;
      const flying = new Set(pending.flying);
      if (values.length === pending.oldValues.length) {
        for (let i = 0; i < values.length; i++) {
          if (values[i] !== pending.oldValues[i]) flying.add(i);
        }
      }
      prevDiceRef.current = {
        rolls,
        order: pending.trayOrder,
        locked,
        values,
      };
      beginTossAnimation({
        trayOrder: pending.trayOrder,
        flying: [...flying].filter((i) => i < values.length), 
        oldValues: pending.oldValues,
        newValues: values,
      });
      return;
    }

    if (prev) {
      if (rolls > prev.rolls) {
        prevDiceRef.current = { rolls, order: prev.order, locked: prev.locked, values };
        const flying = prev.order.filter((index) => !(prev.locked[index] ?? false));
        beginTossAnimation({
          trayOrder: prev.order,
          flying,
          oldValues: prev.values,
          newValues: values,
        });
        return;
      }

      if (!rollAnim && values.length === prev.values.length) {
        const changed: number[] = [];
        for (let i = 0; i < values.length; i++) {
          if (values[i] !== prev.values[i]) changed.push(i);
        }
        // Twins (and similar) change faces without consuming a turn roll.
        if (changed.length >= 2) {
          prevDiceRef.current = { rolls, order: prev.order, locked, values };
          beginTossAnimation({
            trayOrder: prev.order,
            flying: changed,
            oldValues: prev.values,
            newValues: values,
          });
          return;
        }
      }
    }

    if (!rollAnim) {
      prevDiceRef.current = { rolls, order, locked, values };
    }
  }, [match.dice, sortedDice, rollAnim, match.toddler_used_this_turn]);

  // Drop a pending Toddler toss if the turn ends before the update arrives.
  useEffect(() => {
    if (match.phase !== "turn_active") pendingTossRef.current = null;
  }, [match.phase]);
  // After tray reorders to sorted, invert transforms so dice stay on the felt, then snap home L→H.
  useLayoutEffect(() => {
    if (!rollAnim || rollAnim.phase !== "flip" || !match.dice) return;
    if (flipHandledRef.current) return;
    flipHandledRef.current = true;

    const hold: Record<number, DieScatter> = {};
    for (const index of rollAnim.order) {
      const el = dieElsRef.current.get(index);
      const first = rollAnim.firstRects[index];
      if (!el || !first) continue;
      const last = el.getBoundingClientRect();
      hold[index] = {
        x: first.left - last.left,
        y: first.top - last.top,
        rot: rollAnim.scatter[index]?.rot ?? 0,
      };
    }

    const returnOrder = [...rollAnim.order];
    const gen = tossGenRef.current;

    setRollAnim((cur) =>
      cur && cur.phase === "flip"
        ? { ...cur, hold, phase: "back", freezeMotion: true }
        : cur,
    );

    const frame = window.requestAnimationFrame(() => {
      const play = window.requestAnimationFrame(() => {
        if (tossGenRef.current !== gen) return;
        setRollAnim((cur) =>
          cur && cur.phase === "back" ? { ...cur, freezeMotion: false } : cur,
        );
        returnOrder.forEach((index, i) => {
          const t = window.setTimeout(() => {
            if (tossGenRef.current !== gen) return;
            setRollAnim((cur) => {
              if (!cur) return null;
              if (cur.returned.includes(index)) return cur;
              return { ...cur, returned: [...cur.returned, index] };
            });
          }, i * 130);
          rollTimersRef.current.push(t);
        });
        const tDone = window.setTimeout(() => {
          if (tossGenRef.current !== gen) return;
          setRollAnim(null);
        }, returnOrder.length * 130 + 360);
        rollTimersRef.current.push(tDone);
      });
      rollRafRef.current.push(play);
    });
    rollRafRef.current.push(frame);
  }, [rollAnim, match.dice]);

  useEffect(() => {
    return () => {
      clearTossTimers();
    };
  }, []);

  // Where everyone would sit if the leaderboard re-sorted on current totals right now.
  const predictedOrder = useMemo(
    () =>
      [...match.players]
        .sort((a, b) => b.total_score - a.total_score || a.name.localeCompare(b.name))
        .map((p) => p.name),
    [match.players],
  );

  // Frozen placement from the server; scores/chips on each row still update live.
  const displayOrder =
    match.leaderboard_order?.length > 0 ? match.leaderboard_order : predictedOrder;
  const rankedPlayers = displayOrder
    .map((name) => match.players.find((p) => p.name === name))
    .filter((p): p is PlayerState => Boolean(p));

  const sheetPlayerName =
    sheetMode === "current" ? match.active_player : mineSelection;
  const sheetPlayer =
    match.players.find((p) => p.name === sheetPlayerName) ?? match.players[0];

  // Cancel die-targeting when leaving the active turn; keep block-arm while debuffs remain.
  useEffect(() => {
    if (!active || match.phase !== "turn_active") {
      setIcarusArming(false);
      setSpaceArming(false);
      setDiePick(null);
      setPlayerTarget(null);
    }
    if ((me?.queued_hindrances.length ?? 0) === 0) {
      setBlockArming(null);
    }
  }, [active, match.phase, match.dice, me?.queued_hindrances.length]);

  // Shop sign is off-turn only — close the panel when shopping becomes unavailable.
  useEffect(() => {
    if (!canShop) setShopOpen(false);
  }, [canShop]);

  // Jump scoresheet to a player (used by leaderboard name clicks).
  function selectSheetPlayer(name: string) {
    setSheetMode("mine");
    setMineSelection(name);
    setSheetOpen(true);
  }

  function clearAiming() {
    setIcarusArming(false);
    setSpaceArming(false);
    setDiePick(null);
    setBlockArming(null);
    setPlayerTarget(null);
  }

  function armPlayerTarget(mode: PlayerTargetMode) {
    clearAiming();
    setLeftTab("leaderboard");
    setLeftOpen(true);
    setPlayerTarget(mode);
  }

  function selectLeaderboardPlayer(name: string) {
    if (playerTarget && name !== playerName) {
      if (playerTarget.kind === "helping_hand") {
        onAction({
          type: "cast_power",
          card_id: "helping_hand",
          choice: helpingChoice,
          target: name,
        });
      } else {
        onAction({
          type: "cast_hindrance",
          card_id: playerTarget.cardId,
          target: name,
        });
      }
      clearAiming();
      return;
    }
    selectSheetPlayer(name);
  }

  function handleDieClick(index: number, locked: boolean) {
    if (!active) return;
    if (diePick) {
      const need = diePick.mode === "score" ? 5 : 2;
      const already = diePick.picked.includes(index);
      const next = already
        ? diePick.picked.filter((i) => i !== index)
        : [...diePick.picked, index].slice(0, need);
      if (next.length === need) {
        if (diePick.mode === "trading") {
          if (diePick.cardId === "toddler" && match.dice) {
            const trayOrder =
              rollAnim?.order ?? sortedDice.map((d) => d.index);
            pendingTossRef.current = {
              flying: [...next],
              oldValues: [...match.dice.values],
              trayOrder,
            };
          }
          onAction({
            type: "activate_trading",
            card_id: diePick.cardId,
            die_indices: next,
          });
        } else if (diePick.mode === "twins") {
          onAction({ type: "cast_power", card_id: "twins", die_indices: next });
        } else if (diePick.mode === "do_over") {
          onAction({ type: "do_over", die_indices: next });
        } else {
          onAction({
            type: "score",
            category: diePick.category,
            die_indices: next,
          });
        }
        setDiePick(null);
        return;
      }
      setDiePick({ ...diePick, picked: next });
      return;
    }
    if (spaceArming) {
      onAction({
        type: "cast_power",
        card_id: "space_die",
        die_index: index,
        face_value: spaceFace,
      });
      setSpaceArming(false);
      return;
    }
    if (icarusArming) {
      onAction({ type: "cast_power", card_id: "icarus", die_index: index });
      setIcarusArming(false);
      return;
    }
    onAction({ type: locked ? "unlock" : "lock", index });
  }

  function castPower(card: CardInfo) {
    // Clicking an already-armed card cancels targeting (e.g. accidental Icarus).
    if (card.id === "icarus" && icarusArming) {
      clearAiming();
      return;
    }
    if (card.id === "space_die" && spaceArming) {
      clearAiming();
      return;
    }
    if (card.id === "twins" && diePick?.mode === "twins") {
      clearAiming();
      return;
    }
    if (card.id === "twins" && Object.keys(match.twins_links ?? {}).length > 0) {
      clearAiming();
      onAction({ type: "cast_power", card_id: "twins" });
      return;
    }
    if (card.id === "parry" && blockArming === "parry") {
      clearAiming();
      return;
    }
    if (card.id === "helping_hand" && playerTarget?.kind === "helping_hand") {
      clearAiming();
      return;
    }
    if (
      card.id === "parry" &&
      myDebuffs.length > 0 &&
      canArmParry
    ) {
      clearAiming();
      setBlockArming("parry");
      return;
    }
    clearAiming();
    if (!match.dice && card.id !== "write_off" && card.id !== "parry") {
      // most powers need dice; write_off/parry edge cases handled below
    }
    if (card.id === "icarus") {
      if (!match.dice) return;
      setIcarusArming(true);
      return;
    }
    if (card.id === "space_die") {
      if (!match.dice) return;
      setSpaceArming(true);
      return;
    }
    if (card.id === "twins") {
      if (!match.dice) return;
      if ((match.dice.rolls_this_turn ?? 0) < 1) return;
      setDiePick({ mode: "twins", picked: [] });
      return;
    }
    if (card.id === "helping_hand") {
      armPlayerTarget({ kind: "helping_hand" });
      return;
    }
    if (card.id === "do_over") {
      // Do over is used from the scoresheet row, not cast from the fan.
      return;
    }
    onAction({ type: "cast_power", card_id: card.id });
  }

  function castHindrance(card: CardInfo, slotIndex: number) {
    if (
      playerTarget?.kind === "hindrance" &&
      playerTarget.cardId === card.id &&
      playerTarget.slotIndex === slotIndex
    ) {
      clearAiming();
      return;
    }
    if (UNTARGETED_HINDRANCES.has(card.id)) {
      clearAiming();
      onAction({ type: "cast_hindrance", card_id: card.id });
      return;
    }
    armPlayerTarget({ kind: "hindrance", cardId: card.id, slotIndex });
  }

  function requestScore(category: string) {
    const diceCount = match.dice?.values.length ?? 0;
    if (diceCount > 5) {
      setDiePick({ mode: "score", category, picked: [] });
      setIcarusArming(false);
      setSpaceArming(false);
      return;
    }
    onAction({ type: "score", category });
  }

  function requestDoOver() {
    const diceCount = match.dice?.values.length ?? 0;
    if (diceCount > 5) {
      setDiePick({ mode: "do_over", picked: [] });
      setIcarusArming(false);
      setSpaceArming(false);
      return;
    }
    onAction({ type: "do_over" });
  }

  function activateTrading(card: CardInfo) {
    if (card.id === "guardian") {
      if ((me?.guardian_cooldown ?? 0) > 0) return;
      if ((me?.queued_hindrances.length ?? 0) === 0) return;
      if (blockArming === "guardian") {
        clearAiming();
        return;
      }
      clearAiming();
      setBlockArming("guardian");
      return;
    }
    if (!ACTIVATABLE_TRADING.has(card.id)) return;
    if (diePick?.mode === "trading" && diePick.cardId === card.id) {
      clearAiming();
      return;
    }
    clearAiming();
    if (card.id === "toddler" || card.id === "psychic") {
      if (!match.dice) return;
      if (card.id === "toddler" && match.toddler_used_this_turn) return;
      if (card.id === "psychic" && match.psychic_used_this_turn) return;
      if ((match.dice.rolls_this_turn ?? 0) < 1) return;
      setDiePick({
        mode: "trading",
        cardId: card.id,
        picked: [],
      });
      return;
    }
    onAction({ type: "activate_trading", card_id: card.id });
  }

  function tradingDisabled(card: CardInfo): boolean {
    if (card.id === "guardian") {
      return (
        (me?.guardian_cooldown ?? 0) > 0 ||
        (me?.queued_hindrances.length ?? 0) === 0
      );
    }
    if (!active || match.phase !== "turn_active") return true;
    if (card.id === "gambler") {
      const cost = me?.gambler_cost ?? 200;
      return !match.dice || (me?.chips ?? 0) < cost;
    }
    if (card.id === "lawyer") {
      return (me?.lawyer_cooldown ?? 0) > 0;
    }
    if (card.id === "toddler" || card.id === "psychic") {
      const used =
        card.id === "toddler"
          ? Boolean(match.toddler_used_this_turn)
          : Boolean(match.psychic_used_this_turn);
      return (
        !match.dice ||
        used ||
        Boolean(rollAnim) ||
        (match.dice.rolls_this_turn ?? 0) < 1
      );
    }
    return true;
  }

  function tradingLabel(card: CardInfo): string {
    if (card.id === "gambler") {
      return `${label(card.id)} (${me?.gambler_cost ?? 200})`;
    }
    if (diePick?.mode === "trading" && diePick.cardId === card.id) {
      return `${label(card.id)} (${diePick.picked.length}/2)`;
    }
    return label(card.id);
  }

  const canArmParry =
    Boolean(me?.parry_ready) ||
    Boolean(me?.power_cards.some((c) => c.id === "parry"));
  const aiming =
    icarusArming ||
    spaceArming ||
    Boolean(diePick) ||
    Boolean(blockArming) ||
    Boolean(playerTarget);
  const powerFanCards = me?.power_cards ?? [];
  const showParryReadyChip =
    Boolean(me?.parry_ready) && !powerFanCards.some((c) => c.id === "parry");
  const tradingCards = me?.trading_cards ?? [];
  const myPlace =
    rankedPlayers.findIndex((p) => p.name === playerName) + 1 || null;
  const sheetPlace =
    rankedPlayers.findIndex((p) => p.name === sheetPlayer.name) + 1 || null;
  const myDebuffs = me?.queued_hindrances ?? [];
  const activeEffects = me
    ? [
        me.turn_effects.zero_upper ? "Glass half full (upper = 0)" : null,
        me.turn_effects.zero_lower ? "Glass half empty (lower = 0)" : null,
        me.turn_effects.score_bonus
          ? `+${me.turn_effects.score_bonus} score bonus`
          : null,
        me.turn_effects.score_penalty
          ? `−${me.turn_effects.score_penalty} score penalty`
          : null,
      ].filter(Boolean)
    : [];

  return (
    <div className="hud">
      <div className="hud-felt" aria-hidden />

      <header className="hud-topbar">
        <div className="hud-brand">
          <strong>Loaded Dice</strong>
          <span>Room {room.room_code}</span>
        </div>
        <div className="hud-you-stats" aria-label="Your chips, score, and place">
          <span>
            <em>Chips</em> {me?.chips ?? 0}
          </span>
          <span>
            <em>Score</em> {me?.total_score ?? 0}
          </span>
          <span>
            <em>Place</em> {myPlace != null ? `#${myPlace}` : "—"}
          </span>
        </div>
        <div className="hud-status">
          <span>
            Rotation {match.rotation_count} · {label(match.phase)}
          </span>
          <span className={active ? "you-active" : "spectating"}>
            {match.is_over
              ? `Winner: ${match.winner ?? "?"}`
              : active
                ? "Your turn"
                : `${match.active_player} is playing`}
          </span>
        </div>
        <button type="button" className="secondary" onClick={onLeave}>
          Leave
        </button>
      </header>

      <aside className={`hud-dock hud-left ${leftOpen ? "open" : "peek"}`}>
        <div className="dock-body">
          <div className="tab-row">
            <button
              type="button"
              className={leftTab === "history" ? "tab active" : "tab"}
              onClick={() => setLeftTab("history")}
            >
              History
            </button>
            <button
              type="button"
              className={leftTab === "leaderboard" ? "tab active" : "tab"}
              onClick={() => setLeftTab("leaderboard")}
            >
              Leaderboard
            </button>
          </div>

          {leftTab === "history" ? (
            <div className="dock-content">
              {(match.hindrance_feed?.length ?? 0) === 0 ? (
                <p className="hint">No hindrances cast yet.</p>
              ) : (
                <ul className="killfeed">
                  {[...(match.hindrance_feed ?? [])].reverse().map((entry, index) => (
                    <li
                      key={`${entry.rotation}-${entry.card_id}-${entry.caster_name}-${entry.target_name}-${index}`}
                      className={entry.blocked ? "blocked" : ""}
                    >
                      <Tip text={tipText(entry.card_id)} className="tip-below">
                        <span className="killfeed-line">{killfeedLine(entry)}</span>
                      </Tip>
                    </li>
                  ))}
                </ul>
              )}
            </div>
          ) : (
            <ol className="leaderboard">
              {rankedPlayers.map((p, place) => {
                const arrow = placementArrow(p.name, place, predictedOrder);
                const delta = p.score_delta ?? 0;
                return (
                  <li
                    key={p.name}
                    className={p.name === match.active_player ? "playing" : ""}
                  >
                    <button
                      type="button"
                      className={`leaderboard-row ${
                        playerTarget && p.name !== playerName ? "pick-target" : ""
                      } ${
                        playerTarget && p.name === playerName ? "self-blocked" : ""
                      }`}
                      disabled={Boolean(playerTarget && p.name === playerName)}
                      onClick={() => selectLeaderboardPlayer(p.name)}
                    >
                      <span className="name-link">
                        <span className="place">#{place + 1}</span>
                        <span className="name">{p.name}</span>
                        {arrow === "up" && (
                          <span
                            className="place-arrow up"
                            title="Predicted to rise next rotation"
                          >
                            ▲
                          </span>
                        )}
                        {arrow === "down" && (
                          <span
                            className="place-arrow down"
                            title="Predicted to fall next rotation"
                          >
                            ▼
                          </span>
                        )}
                      </span>
                      <span className="stats">
                        {p.total_score} pts{" "}
                        <span
                          className={`score-delta ${delta > 0 ? "up" : delta < 0 ? "down" : ""}`}
                          title="Net score change this rotation"
                        >
                          ({formatScoreDelta(delta)})
                        </span>
                        {" · "}
                        {p.chips} chips
                      </span>
                    </button>
                  </li>
                );
              })}
            </ol>
          )}
        </div>
        <button
          type="button"
          className="dock-toggle"
          onClick={() => setLeftOpen((v) => !v)}
          aria-label={leftOpen ? "Hide left panel" : "Show left panel"}
        >
          {leftOpen ? "‹" : "›"}
        </button>
      </aside>

      <aside
        className={`hud-dock hud-sheet ${sheetOpen ? "open" : "peek"} ${
          sheetFullscreen ? "fullscreen" : ""
        }`}
      >
        <button
          type="button"
          className="dock-toggle"
          onClick={() => setSheetOpen((v) => !v)}
          aria-label={sheetOpen ? "Hide scoresheet" : "Show scoresheet"}
        >
          {sheetOpen ? "›" : "‹"}
        </button>
        <div className="dock-body">
          <div className="sheet-controls">
            <button
              type="button"
              className={sheetMode === "mine" ? "tab active" : "tab"}
              onClick={() => {
                setMineSelection(playerName);
                setSheetMode("mine");
              }}
            >
              Mine
            </button>
            <button
              type="button"
              className={sheetMode === "current" ? "tab active" : "tab"}
              onClick={() => setSheetMode("current")}
            >
              Current player
            </button>
            <button
              type="button"
              className="secondary sheet-full-btn"
              onClick={() => setSheetFullscreen((v) => !v)}
            >
              {sheetFullscreen ? "Exit full" : "Fullscreen"}
            </button>
          </div>
          {sheetMode === "mine" && (
            <select
              className="sheet-player-select"
              value={mineSelection}
              onChange={(e) => setMineSelection(e.target.value)}
            >
              {match.players.map((p) => (
                <option key={p.name} value={p.name}>
                  {p.name}
                  {p.name === playerName ? " (you)" : ""}
                </option>
              ))}
            </select>
          )}
          <p className="sheet-heading">
            {sheetPlayer.name}
            {sheetMode === "current" ? " · live turn" : ""}
          </p>
          <p className="sheet-summary">
            {sheetPlayer.total_score} pts · {sheetPlayer.chips} chips
            {sheetPlace != null ? ` · #${sheetPlace}` : ""}
          </p>
          <ScoreSheetTable
            player={sheetPlayer}
            previews={
              sheetPlayer.name === match.active_player ? match.previews : null
            }
            doOverPreview={
              sheetPlayer.name === match.active_player
                ? (match.do_over_preview ?? null)
                : null
            }
            canScore={
              active &&
              sheetPlayer.name === playerName &&
              match.phase === "turn_active" &&
              !aiming &&
              Boolean(match.dice && match.dice.rolls_this_turn >= 1)
            }
            canDoOver={
              active &&
              sheetPlayer.name === playerName &&
              match.phase === "turn_active" &&
              !aiming &&
              Boolean(match.do_over_preview) &&
              Boolean(match.dice && match.dice.rolls_this_turn >= 1)
            }
            onScore={requestScore}
            onDoOver={requestDoOver}
          />
        </div>
      </aside>

      <main className="hud-table">
        {match.forecaster_reveals && (
          <div className="forecaster-panel">
            <h3>Forecaster</h3>
            {Object.entries(match.forecaster_reveals).map(([name, cards]) => (
              <div key={name}>
                <strong>{name}:</strong>{" "}
                {cards.length === 0
                  ? "no hindrances"
                  : cards.map((id) => label(id)).join(", ")}
              </div>
            ))}
          </div>
        )}

        {match.dice && (
          <div
            className={`dice-tray ${aiming ? "targeting" : ""} ${
              rollAnim ? "rolling" : ""
            }`}
          >
            {trayDice.map(({ value, index, locked, kind }) => {
              const psychicFace = match.psychic_previews?.[String(index)];
              const picked = diePick?.picked.includes(index);
              const kindClass = kind !== "standard" ? `die-${kind}` : "";
              const twinsLinked = Boolean(
                match.twins_links &&
                  (Object.keys(match.twins_links).includes(String(index)) ||
                    Object.values(match.twins_links).includes(index)),
              );
              const isFlying = Boolean(rollAnim?.flying.includes(index));
              const isReturned = Boolean(rollAnim?.returned.includes(index));
              const scatter = rollAnim?.scatter[index];
              const hold = rollAnim?.hold[index];
              const phase = rollAnim?.phase;
              let pose: DieScatter | null = null;
              if (rollAnim && !isReturned) {
                if (phase === "out" && isFlying && scatter) {
                  pose = scatter;
                } else if ((phase === "flip" || phase === "back") && hold) {
                  pose = hold;
                }
              }
              const dieStyle = pose
                ? {
                    transform: `translate(${pose.x}px, ${pose.y}px) rotate(${pose.rot}deg)`,
                  }
                : undefined;
              return (
                <div
                  key={index}
                  className={`die-slot ${
                    isFlying && !isReturned ? "die-slot-flying" : ""
                  }`}
                >
                  {psychicFace != null && !rollAnim && (
                    <span
                      className={`die die-psychic-preview ${kindClass}`}
                      aria-hidden
                    >
                      {psychicFace}
                    </span>
                  )}
                  <button
                    type="button"
                    ref={(el) => {
                      if (el) dieElsRef.current.set(index, el);
                      else dieElsRef.current.delete(index);
                    }}
                    className={`die ${locked ? "locked" : ""} ${kindClass} ${
                      aiming ? "targetable" : ""
                    } ${picked ? "picked" : ""} ${
                      twinsLinked ? "die-twins" : ""
                    } ${rollAnim ? "die-fly" : ""} ${
                      pose ? "die-scattered" : ""
                    } ${isReturned ? "die-returned" : ""} ${
                      rollAnim?.freezeMotion ? "die-no-motion" : ""
                    }`}
                    style={dieStyle}
                    disabled={!active || Boolean(rollAnim)}
                    onClick={() => handleDieClick(index, locked)}
                  >
                    {value}
                  </button>
                </div>
              );
            })}
            <span className="dice-meta">
              {diePick?.mode === "score"
                ? `Pick ${5 - diePick.picked.length} more die(s) to score ${label(diePick.category)}`
                    : diePick?.mode === "twins"
                      ? `Pick ${2 - diePick.picked.length} more: 1st is source, 2nd copies it on the next roll`
                      : diePick?.mode === "trading"
                    ? `Pick ${2 - diePick.picked.length} more die(s) for ${label(diePick.cardId)}`
                    : spaceArming
                      ? `Click a die to set it to ${spaceFace}`
                      : icarusArming
                        ? "Click a die to bump"
                        : `${match.dice.rolls_this_turn}/${match.dice.max_rolls} rolls`}
            </span>
          </div>
        )}

        <div className="table-actions">
          {match.phase === "between_turns" && active && !match.is_over && (
            <button type="button" onClick={() => onAction({ type: "start_turn" })}>
              Start turn
            </button>
          )}
          {blockArming && (
            <p className="hint table-hint">
              Click a purple debuff to block with {label(blockArming)} (or click the
              card again to cancel)
            </p>
          )}
          {match.phase === "turn_active" && active && (
            <>
              <button
                type="button"
                onClick={() => onAction({ type: "roll" })}
                disabled={aiming || !match.dice || Boolean(rollAnim)}
              >
                Roll
              </button>
              {spaceArming && (
                <label className="face-picker">
                  Face
                  <select
                    value={spaceFace}
                    onChange={(e) => setSpaceFace(Number(e.target.value))}
                  >
                    {[1, 2, 3, 4, 5, 6].map((n) => (
                      <option key={n} value={n}>
                        {n}
                      </option>
                    ))}
                  </select>
                </label>
              )}
              {(powerFanCards.some((c) => c.id === "helping_hand") ||
                playerTarget?.kind === "helping_hand") && (
                <label className="face-picker">
                  Helping hand
                  <select
                    value={helpingChoice}
                    onChange={(e) =>
                      setHelpingChoice(e.target.value as "chips" | "points")
                    }
                  >
                    <option value="chips">I take chips</option>
                    <option value="points">I take +10 pts</option>
                  </select>
                </label>
              )}
              {aiming && (
                <button type="button" className="secondary" onClick={clearAiming}>
                  Cancel aim
                </button>
              )}
              {playerTarget && (
                <p className="hint table-hint target-prompt">
                  Choose your target on the leaderboard
                  {playerTarget.kind === "helping_hand"
                    ? " for helping hand"
                    : ` for ${label(playerTarget.cardId)}`}{" "}
                  (click the card again to cancel)
                </p>
              )}
            </>
          )}
          {!active && !match.is_over && (
            <p className="hint table-hint">Spectating {match.active_player}…</p>
          )}
          {match.is_over && (
            <button type="button" className="secondary" onClick={onLeave}>
              Back to lobby
            </button>
          )}
        </div>
      </main>

      <section className={`hud-cards ${cardsOpen ? "open" : "peek"}`}>
        <button
          type="button"
          className="dock-toggle cards-toggle"
          onClick={() => setCardsOpen((v) => !v)}
          aria-label={cardsOpen ? "Hide cards" : "Show cards"}
        >
          {cardsOpen ? "▾" : "▴"}
        </button>

        <div className="card-trays">
          <div className="card-tray debuff-tray">
            <span className="tray-label">Debuffs</span>
            <div className={`fan ${blockArming ? "block-targeting" : ""}`}>
              {myDebuffs.length === 0 && (
                <span className="empty-fan muted">None</span>
              )}
              {myDebuffs.map((h, i) => (
                <Tip
                  key={`d-${h.card_id}-${i}`}
                  text={debuffOnYouTip(h.card_id, h.caster_name)}
                  tipAlign="start"
                >
                  <button
                    type="button"
                    className={`fan-card debuff ${blockArming ? "targetable" : ""}`}
                    style={{ zIndex: i + 1 }}
                    disabled={!blockArming}
                    onClick={() => {
                      if (!blockArming) return;
                      onAction({
                        type: "block_hindrance",
                        hindrance_index: i,
                        blocker_card_id: blockArming,
                      });
                      clearAiming();
                    }}
                  >
                    {label(h.card_id)}
                  </button>
                </Tip>
              ))}
            </div>
            {activeEffects.length > 0 && (
              <ul className="active-effect-strip">
                {activeEffects.map((text) => (
                  <li key={String(text)}>{text}</li>
                ))}
              </ul>
            )}
          </div>

          <div className="card-tray power-tray">
            <span className="tray-label">Power</span>
            <div className="fan">
              {powerFanCards.length === 0 && !showParryReadyChip && (
                <span className="empty-fan muted">Empty</span>
              )}
              {powerFanCards.map((card, i) => {
                const isHindrance = HINDRANCE_IDS.has(card.id);
                const status = conditionStatus(card.id, me, match.rotation_count);
                const cd = cooldownTurnsLeft(card.id, me);
                const armed = isHindrance
                  ? playerTarget?.kind === "hindrance" &&
                    playerTarget.cardId === card.id &&
                    playerTarget.slotIndex === i
                  : (card.id === "icarus" && icarusArming) ||
                    (card.id === "space_die" && spaceArming) ||
                    (card.id === "twins" &&
                      (diePick?.mode === "twins" ||
                        Object.keys(match.twins_links ?? {}).length > 0)) ||
                    (card.id === "parry" && blockArming === "parry") ||
                    (card.id === "helping_hand" &&
                      playerTarget?.kind === "helping_hand");
                return (
                <Tip
                  key={`p-${card.id}-${i}`}
                  text={tipText(card.id, card.transparent)}
                  tipAlign="start"
                >
                  <button
                    type="button"
                    className={`fan-card ${isHindrance ? "hindrance" : "power"} ${
                      armed ? "armed" : ""
                    } ${cd > 0 ? "on-cooldown" : ""} ${
                      status === "DORMANT" ? "dormant" : ""
                    }`}
                    disabled={
                      card.id === "parry"
                        ? !(
                            (myDebuffs.length > 0 && canArmParry) ||
                            (active &&
                              match.phase === "turn_active" &&
                              canArmParry)
                          )
                        : !active ||
                          (!isHindrance &&
                            (card.id === "do_over" ||
                              ((card.id === "icarus" ||
                                card.id === "space_die" ||
                                card.id === "twins" ||
                                card.id === "super_serum" ||
                                card.id === "benchwarmer" ||
                                card.id === "boolean") &&
                                !match.dice)))
                    }
                    onClick={() =>
                      isHindrance ? castHindrance(card, i) : castPower(card)
                    }
                    style={{ zIndex: i + 1 }}
                  >
                    <CardFace
                      cardId={card.id}
                      me={me}
                      rotationCount={match.rotation_count}
                    />
                  </button>
                </Tip>
                );
              })}
              {showParryReadyChip && myDebuffs.length > 0 && (
                <Tip text={tipText("parry")} tipAlign="start">
                  <button
                    type="button"
                    className={`fan-card power ${blockArming === "parry" ? "armed" : ""}`}
                    disabled={myDebuffs.length === 0}
                    onClick={() => {
                      if (blockArming === "parry") {
                        clearAiming();
                        return;
                      }
                      clearAiming();
                      setBlockArming("parry");
                    }}
                    style={{ zIndex: powerFanCards.length + 1 }}
                  >
                    parry
                  </button>
                </Tip>
              )}
            </div>
          </div>

          <div className="card-tray trading-tray">
            <span className="tray-label">Trading</span>
            <div className="fan">
              {tradingCards.length === 0 && (
                <span className="empty-fan muted">Empty</span>
              )}
              {tradingCards.map((card, i) =>
                ACTIVATABLE_TRADING.has(card.id) || card.id === "guardian" ? (
                  <Tip
                    key={`t-${card.id}-${i}`}
                    tipAlign="end"
                    text={tipText(
                      card.id,
                      false,
                      card.id === "gambler"
                        ? `Cost ${me?.gambler_cost ?? 200} chips.`
                        : card.id === "lawyer" && (me?.lawyer_cooldown ?? 0) > 0
                          ? `Cooldown: ${me?.lawyer_cooldown} turns.`
                          : card.id === "guardian" && (me?.guardian_cooldown ?? 0) > 0
                            ? `Cooldown: ${me?.guardian_cooldown} turns.`
                            : card.id === "toddler" && match.toddler_used_this_turn
                              ? "Already used this turn."
                              : card.id === "psychic" && match.psychic_used_this_turn
                                ? "Already used this turn."
                                : undefined,
                    )}
                  >
                    <button
                      type="button"
                      className={`fan-card trading ${
                        (diePick?.mode === "trading" && diePick.cardId === card.id) ||
                        (card.id === "guardian" && blockArming === "guardian")
                          ? "armed"
                          : ""
                      } ${cooldownTurnsLeft(card.id, me) > 0 ? "on-cooldown" : ""}`}
                      style={{ zIndex: i + 1 }}
                      disabled={tradingDisabled(card)}
                      onClick={() => activateTrading(card)}
                    >
                      <CardFace
                        cardId={card.id}
                        me={me}
                        rotationCount={match.rotation_count}
                        title={tradingLabel(card)}
                      />
                    </button>
                  </Tip>
                ) : (
                  <Tip key={`t-${card.id}-${i}`} tipAlign="end" text={tipText(card.id)}>
                    <div
                      className="fan-card trading passive"
                      style={{ zIndex: i + 1 }}
                    >
                      <CardFace
                        cardId={card.id}
                        me={me}
                        rotationCount={match.rotation_count}
                        title={tradingLabel(card)}
                      />
                    </div>
                  </Tip>
                ),
              )}
            </div>
          </div>
        </div>
      </section>

      {canShop && (
        <button
          type="button"
          className={`shop-sign ${shopOpen ? "open" : ""}`}
          onClick={() => setShopOpen((v) => !v)}
        >
          Shop
        </button>
      )}

      {canShop && shopOpen && (
        <div className="shop-panel">
          <div className="shop-panel-head">
            <h2>Shop</h2>
            <span className="hint">{me?.chips ?? 0} chips</span>
            <button type="button" className="secondary" onClick={() => setShopOpen(false)}>
              Close
            </button>
          </div>
          <ul className="shop-list">
            {match.shop.stock.map((offer) => (
              <li key={offer.index}>
                <Tip text={tipText(offer.card_id)} className="tip-below">
                  <span>
                    {label(offer.card_id)} — {offer.price}
                  </span>
                </Tip>
                <button
                  type="button"
                  onClick={() => onAction({ type: "buy", stock_index: offer.index })}
                >
                  Buy
                </button>
              </li>
            ))}
          </ul>
          <button
            type="button"
            className="secondary"
            onClick={() => onAction({ type: "reroll_shop" })}
          >
            Reroll ({match.shop.reroll_cost})
          </button>
        </div>
      )}
    </div>
  );
}

function ScoreSheetTable({
  player,
  previews,
  doOverPreview,
  canScore,
  canDoOver,
  onScore,
  onDoOver,
}: {
  player: PlayerState;
  previews: Record<string, number> | null;
  doOverPreview: { category: string; points: number } | null;
  canScore: boolean;
  canDoOver: boolean;
  onScore: (category: string) => void;
  onDoOver: () => void;
}) {
  function summaryScore(id: string): string {
    if (id === "bonus") {
      const bonus = player.upper_bonus ?? 0;
      return bonus > 0 ? String(bonus) : "—";
    }
    if (id === "top_half_total") {
      return String(player.upper_subtotal ?? 0);
    }
    if (id === "lower_half_total") {
      return String(player.lower_subtotal ?? 0);
    }
    if (id === "total") {
      return String(player.sheet_total ?? player.total_score);
    }
    if (id === "yahtzee_bonus") {
      const count = player.yahtzee_bonus_count ?? 0;
      return count > 0 ? "X".repeat(count) : "—";
    }
    return "—";
  }

  return (
    <table className="sheet">
      <thead>
        <tr>
          <th>Category</th>
          <th>Score</th>
          <th>Preview</th>
          <th />
        </tr>
      </thead>
      <tbody>
        {SHEET_ROWS.map((row) => {
          if (row.kind === "summary") {
            const tip = CATEGORY_HOVER[row.id] ?? "";
            return (
              <tr key={row.id} className="sheet-summary-row">
                <td>
                  <Tip text={tip}>
                    <span className="sheet-cat-name">
                      {SUMMARY_LABELS[row.id] ?? label(row.id)}
                    </span>
                  </Tip>
                </td>
                <td>{summaryScore(row.id)}</td>
                <td className="muted" />
                <td />
              </tr>
            );
          }

          const category = row.id;
          const filled = player.sheet[category];
          const preview = previews?.[category];
          const open = filled == null;
          const isDoOverTarget =
            doOverPreview != null && doOverPreview.category === category;
          const tip = CATEGORY_HOVER[category] ?? "";
          return (
            <tr
              key={category}
              className={isDoOverTarget ? "do-over-row" : undefined}
            >
              <td>
                <Tip text={tip}>
                  <span className="sheet-cat-name">{label(category)}</span>
                </Tip>
              </td>
              <td>{filled == null ? "—" : filled}</td>
              <td
                className={isDoOverTarget ? "do-over-preview" : "muted"}
                title={isDoOverTarget ? "consumes do over" : undefined}
              >
                {isDoOverTarget
                  ? doOverPreview.points
                  : preview == null
                    ? ""
                    : preview}
              </td>
              <td>
                {canDoOver && isDoOverTarget && (
                  <Tip text="consumes do over">
                    <button
                      type="button"
                      className="do-over-btn"
                      onClick={onDoOver}
                    >
                      Do over
                    </button>
                  </Tip>
                )}
                {canScore && open && (
                  <button type="button" onClick={() => onScore(category)}>
                    Score
                  </button>
                )}
              </td>
            </tr>
          );
        })}
      </tbody>
    </table>
  );
}

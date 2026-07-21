import { useEffect, useMemo, useState } from "react";
import { cardBlurb, cardTipLabel } from "./cardCopy";
import { Tip } from "./Tip";
import type { CardInfo, MatchState, PlayerState, RoomState } from "./types";

type Props = {
  room: RoomState;
  playerName: string;
  onAction: (action: Record<string, unknown>) => void;
  onLeave: () => void;
};

const CATEGORIES = [
  "ones",
  "twos",
  "threes",
  "fours",
  "fives",
  "sixes",
  "three_of_a_kind",
  "four_of_a_kind",
  "full_house",
  "small_straight",
  "large_straight",
  "yahtzee",
  "chance",
];

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
  | { mode: "score"; category: string; picked: number[] };

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
  const [hindranceTarget, setHindranceTarget] = useState(
    () => match.players.find((p) => p.name !== playerName)?.name ?? "",
  );
  const [icarusArming, setIcarusArming] = useState(false);
  const [spaceArming, setSpaceArming] = useState(false);
  const [spaceFace, setSpaceFace] = useState(6);
  const [helpingChoice, setHelpingChoice] = useState<"chips" | "points">("chips");
  const [diePick, setDiePick] = useState<DiePickMode | null>(null);
  const [blockArming, setBlockArming] = useState<"parry" | "guardian" | null>(null);

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

  // Display faces low→high, but keep each die's original index for lock/Icarus actions.
  const sortedDice = useMemo(() => {
    if (!match.dice) return [];
    return match.dice.values
      .map((value, index) => ({
        value,
        index,
        locked: match.dice!.locked[index],
      }))
      .sort((a, b) => a.value - b.value || a.index - b.index); 
  }, [match.dice]);

  // Cancel die-targeting / block-arm modes if the turn leaves turn_start/active.
  useEffect(() => {
    if (!active || (match.phase !== "turn_active" && match.phase !== "turn_start")) {
      setIcarusArming(false);
      setSpaceArming(false);
      setDiePick(null);
      setBlockArming(null);
      return;
    }
    if (match.phase !== "turn_active" || !match.dice) {
      setIcarusArming(false);
      setSpaceArming(false);
      setDiePick(null);
    }
    if (match.phase !== "turn_start") {
      setBlockArming(null);
    }
  }, [active, match.phase, match.dice]);

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
          onAction({
            type: "activate_trading",
            card_id: diePick.cardId,
            die_indices: next,
          });
        } else if (diePick.mode === "twins") {
          onAction({ type: "cast_power", card_id: "twins", die_indices: next });
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
    if (card.id === "parry" && blockArming === "parry") {
      clearAiming();
      return;
    }
    if (card.id === "parry" && match.phase === "turn_start" && active) {
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
      setDiePick({ mode: "twins", picked: [] });
      return;
    }
    if (card.id === "helping_hand") {
      const target =
        hindranceTarget ||
        match.players.find((p) => p.name !== playerName)?.name;
      if (!target) return;
      onAction({
        type: "cast_power",
        card_id: "helping_hand",
        choice: helpingChoice,
        target,
      });
      return;
    }
    onAction({ type: "cast_power", card_id: card.id });
  }

  function castHindrance(card: CardInfo) {
    clearAiming();
    if (UNTARGETED_HINDRANCES.has(card.id)) {
      onAction({ type: "cast_hindrance", card_id: card.id });
      return;
    }
    if (!hindranceTarget) return;
    onAction({
      type: "cast_hindrance",
      card_id: card.id,
      target: hindranceTarget,
    });
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

  function activateTrading(card: CardInfo) {
    if (card.id === "guardian") {
      if (!active || match.phase !== "turn_start") return;
      if ((me?.guardian_cooldown ?? 0) > 0) return;
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
        !active ||
        match.phase !== "turn_start" ||
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
      return !match.dice;
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
    icarusArming || spaceArming || Boolean(diePick) || Boolean(blockArming);
  const powerCards = me?.power_cards.filter((c) => !HINDRANCE_IDS.has(c.id)) ?? [];
  const showParryReadyChip =
    Boolean(me?.parry_ready) && !powerCards.some((c) => c.id === "parry");
  const hindranceCards =
    me?.power_cards.filter((c) => HINDRANCE_IDS.has(c.id)) ?? [];
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
                      className="leaderboard-row"
                      onClick={() => selectSheetPlayer(p.name)}
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
            canScore={
              active &&
              sheetPlayer.name === playerName &&
              match.phase === "turn_active" &&
              !aiming &&
              Boolean(match.dice && match.dice.rolls_this_turn >= 1)
            }
            onScore={requestScore}
          />
        </div>
      </aside>

      <main className="hud-table">
        <div className="table-actions">
          {match.phase === "between_turns" && active && !match.is_over && (
            <button type="button" onClick={() => onAction({ type: "start_turn" })}>
              Start turn
            </button>
          )}
          {match.phase === "turn_start" && active && (
            <>
              <button type="button" onClick={() => onAction({ type: "begin_rolling" })}>
                Begin rolling
              </button>
              {blockArming && (
                <p className="hint table-hint">
                  Click a purple debuff to block with {label(blockArming)} (or click the
                  card again to cancel)
                </p>
              )}
            </>
          )}
          {match.phase === "turn_active" && active && (
            <>
              <button
                type="button"
                onClick={() => onAction({ type: "roll" })}
                disabled={aiming || !match.dice}
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
              {powerCards.some((c) => c.id === "helping_hand") && (
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
          <div className={`dice-tray ${aiming ? "targeting" : ""}`}>
            {sortedDice.map(({ value, index, locked }) => {
              const psychicFace = match.psychic_previews?.[String(index)];
              const picked = diePick?.picked.includes(index);
              return (
                <button
                  key={index}
                  type="button"
                  className={`die ${locked ? "locked" : ""} ${
                    aiming ? "targetable" : ""
                  } ${picked ? "picked" : ""}`}
                  disabled={!active}
                  onClick={() => handleDieClick(index, locked)}
                >
                  {value}
                  {psychicFace != null && (
                    <span className="psychic-note">→{psychicFace}</span>
                  )}
                </button>
              );
            })}
            <span className="dice-meta">
              {diePick?.mode === "score"
                ? `Pick ${5 - diePick.picked.length} more die(s) to score ${label(diePick.category)}`
                : diePick?.mode === "twins"
                  ? `Pick ${2 - diePick.picked.length} more die(s) for twins`
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
              {powerCards.length === 0 && (
                <span className="empty-fan muted">Empty</span>
              )}
              {powerCards.map((card, i) => {
                const status = conditionStatus(card.id, me, match.rotation_count);
                const cd = cooldownTurnsLeft(card.id, me);
                return (
                <Tip
                  key={`p-${card.id}-${i}`}
                  text={tipText(card.id, card.transparent)}
                  tipAlign="start"
                >
                  <button
                    type="button"
                    className={`fan-card power ${
                      (card.id === "icarus" && icarusArming) ||
                      (card.id === "space_die" && spaceArming) ||
                      (card.id === "twins" && diePick?.mode === "twins") ||
                      (card.id === "parry" && blockArming === "parry")
                        ? "armed"
                        : ""
                    } ${cd > 0 ? "on-cooldown" : ""} ${
                      status === "DORMANT" ? "dormant" : ""
                    }`}
                    disabled={
                      !active ||
                      (card.id === "parry"
                        ? match.phase !== "turn_start" ||
                          !canArmParry ||
                          myDebuffs.length === 0
                        : (card.id === "icarus" ||
                            card.id === "space_die" ||
                            card.id === "twins" ||
                            card.id === "super_serum" ||
                            card.id === "benchwarmer" ||
                            card.id === "boolean" ||
                            card.id === "do_over") &&
                          !match.dice)
                    }
                    onClick={() => castPower(card)}
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
              {showParryReadyChip && match.phase === "turn_start" && active && (
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
                    style={{ zIndex: powerCards.length + 1 }}
                  >
                    parry
                  </button>
                </Tip>
              )}
            </div>
            {active && hindranceCards.length > 0 && (
              <div className="hindrance-cast">
                <select
                  value={hindranceTarget}
                  onChange={(e) => setHindranceTarget(e.target.value)}
                >
                  {match.players
                    .filter((p) => p.name !== playerName)
                    .map((p) => (
                      <option key={p.name} value={p.name}>
                        {p.name}
                      </option>
                    ))}
                </select>
                {hindranceCards.map((card, i) => {
                  const status = conditionStatus(card.id, me, match.rotation_count);
                  return (
                  <Tip key={`h-${card.id}-${i}`} text={tipText(card.id, card.transparent)}>
                    <button
                      type="button"
                      className={`fan-card hindrance ${
                        status === "DORMANT" ? "dormant" : ""
                      }`}
                      disabled={
                        !UNTARGETED_HINDRANCES.has(card.id) && !hindranceTarget
                      }
                      onClick={() => castHindrance(card)}
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
              </div>
            )}
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
  canScore,
  onScore,
}: {
  player: PlayerState;
  previews: Record<string, number> | null;
  canScore: boolean;
  onScore: (category: string) => void;
}) {
  return (
    <table className="sheet">
      <thead>
        <tr>
          <th>Category</th>
          <th>Score</th>
          <th>Prev</th>
          <th />
        </tr>
      </thead>
      <tbody>
        {CATEGORIES.map((category) => {
          const filled = player.sheet[category];
          const preview = previews?.[category];
          const open = filled == null;
          return (
            <tr key={category}>
              <td>{label(category)}</td>
              <td>{filled == null ? "—" : filled}</td>
              <td className="muted">{preview == null ? "" : preview}</td>
              <td>
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

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
]);

/** Trading cards clicked to activate (stay in party). Others are passives / turn-start. */
const ACTIVATABLE_TRADING = new Set(["gambler", "lawyer", "toddler", "psychic"]);
const DIE_PICK_TRADING = new Set(["toddler", "psychic"]);

type SheetMode = "mine" | "current";
type LeftTab = "debuffs" | "leaderboard";
type DiePickMode = { cardId: "toddler" | "psychic"; picked: number[] };

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
  const [diePick, setDiePick] = useState<DiePickMode | null>(null);

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

  // Cancel die-targeting modes if the turn ends or dice disappear.
  useEffect(() => {
    if (!active || match.phase !== "turn_active" || !match.dice) {
      setIcarusArming(false);
      setDiePick(null);
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

  function handleDieClick(index: number, locked: boolean) {
    if (!active) return;
    if (diePick) {
      const already = diePick.picked.includes(index);
      const next = already
        ? diePick.picked.filter((i) => i !== index)
        : [...diePick.picked, index].slice(0, 2);
      if (next.length === 2) {
        onAction({
          type: "activate_trading",
          card_id: diePick.cardId,
          die_indices: next,
        });
        setDiePick(null);
        return;
      }
      setDiePick({ ...diePick, picked: next });
      return;
    }
    // While Icarus is armed, a die click casts instead of lock/unlock.
    if (icarusArming) {
      onAction({ type: "cast_power", card_id: "icarus", die_index: index });
      setIcarusArming(false);
      return;
    }
    onAction({ type: locked ? "unlock" : "lock", index });
  }

  function castPower(card: CardInfo) {
    setDiePick(null);
    // Icarus needs a die target: first click arms, second click is on a die.
    if (card.id === "icarus") {
      if (!match.dice) return;
      setIcarusArming((armed) => !armed);
      return;
    }
    setIcarusArming(false);
    onAction({ type: "cast_power", card_id: card.id });
  }

  function castHindrance(card: CardInfo) {
    if (!hindranceTarget) return;
    setIcarusArming(false);
    setDiePick(null);
    onAction({
      type: "cast_hindrance",
      card_id: card.id,
      target: hindranceTarget,
    });
  }

  function activateTrading(card: CardInfo) {
    if (!ACTIVATABLE_TRADING.has(card.id)) return;
    setIcarusArming(false);
    if (DIE_PICK_TRADING.has(card.id)) {
      if (!match.dice) return;
      setDiePick((current) =>
        current?.cardId === card.id
          ? null
          : { cardId: card.id as "toddler" | "psychic", picked: [] },
      );
      return;
    }
    setDiePick(null);
    onAction({ type: "activate_trading", card_id: card.id });
  }

  function tradingDisabled(card: CardInfo): boolean {
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
    if (card.id === "lawyer" && (me?.lawyer_cooldown ?? 0) > 0) {
      return `${label(card.id)} (CD ${me?.lawyer_cooldown})`;
    }
    if (card.id === "guardian" && (me?.guardian_cooldown ?? 0) > 0) {
      return `${label(card.id)} (CD ${me?.guardian_cooldown})`;
    }
    if (diePick?.cardId === card.id) {
      return `${label(card.id)} (${diePick.picked.length}/2)`;
    }
    return label(card.id);
  }

  function canParry(): boolean {
    if (!me) return false;
    if (me.parry_ready) return true;
    if (me.power_cards.some((c) => c.id === "parry")) return true;
    if (
      me.trading_cards.some((c) => c.id === "guardian") &&
      (me.guardian_cooldown ?? 0) === 0
    ) {
      return true;
    }
    return false;
  }

  const powerCards = me?.power_cards.filter((c) => !HINDRANCE_IDS.has(c.id)) ?? [];
  const hindranceCards =
    me?.power_cards.filter((c) => HINDRANCE_IDS.has(c.id)) ?? [];
  const tradingCards = me?.trading_cards ?? [];
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
              className={leftTab === "debuffs" ? "tab active" : "tab"}
              onClick={() => setLeftTab("debuffs")}
            >
              Debuffs
            </button>
            <button
              type="button"
              className={leftTab === "leaderboard" ? "tab active" : "tab"}
              onClick={() => setLeftTab("leaderboard")}
            >
              Leaderboard
            </button>
          </div>

          {leftTab === "debuffs" ? (
            <div className="dock-content">
              {match.phase === "turn_start" &&
                active &&
                myDebuffs.map((h, index) => (
                  <div key={`${h.card_id}-${index}`} className="debuff-row">
                    <Tip text={tipText(h.card_id)} className="tip-below">
                      <span>
                        {label(h.card_id)}
                        <span className="muted"> from {h.caster_name}</span>
                      </span>
                    </Tip>
                    <button
                      type="button"
                      className="inline"
                      disabled={!canParry()}
                      onClick={() =>
                        onAction({ type: "block_hindrance", hindrance_index: index })
                      }
                    >
                      Parry
                    </button>
                  </div>
                ))}
              {myDebuffs.length === 0 && activeEffects.length === 0 && (
                <p className="hint">No debuffs on you.</p>
              )}
              {myDebuffs.length > 0 && match.phase !== "turn_start" && (
                <ul className="plain-list">
                  {myDebuffs.map((h, index) => (
                    <li key={`q-${h.card_id}-${index}`}>
                      <Tip text={tipText(h.card_id)} className="tip-below">
                        <span>
                          {label(h.card_id)}{" "}
                          <span className="muted">({h.caster_name})</span>
                        </span>
                      </Tip>
                    </li>
                  ))}
                </ul>
              )}
              {activeEffects.length > 0 && (
                <ul className="plain-list">
                  {activeEffects.map((text) => (
                    <li key={String(text)}>{text}</li>
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
                  <li key={p.name} className={p.name === match.active_player ? "playing" : ""}>
                    <button
                      type="button"
                      className="name-link"
                      onClick={() => selectSheetPlayer(p.name)}
                    >
                      <span className="place">#{place + 1}</span>
                      <span className="name">{p.name}</span>
                      {arrow === "up" && (
                        <span className="place-arrow up" title="Predicted to rise next rotation">
                          ▲
                        </span>
                      )}
                      {arrow === "down" && (
                        <span className="place-arrow down" title="Predicted to fall next rotation">
                          ▼
                        </span>
                      )}
                    </button>
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
              onClick={() => setSheetMode("mine")}
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
          <ScoreSheetTable
            player={sheetPlayer}
            previews={
              sheetPlayer.name === match.active_player ? match.previews : null
            }
            canScore={
              active &&
              sheetPlayer.name === playerName &&
              match.phase === "turn_active" &&
              !icarusArming &&
              Boolean(match.dice && match.dice.rolls_this_turn >= 1)
            }
            onScore={(category) => onAction({ type: "score", category })}
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
            <button type="button" onClick={() => onAction({ type: "begin_rolling" })}>
              Begin rolling
            </button>
          )}
          {match.phase === "turn_active" && active && (
            <>
              <button
                type="button"
                onClick={() => onAction({ type: "roll" })}
                disabled={icarusArming || Boolean(diePick) || !match.dice}
              >
                Roll
              </button>
              <button
                type="button"
                className="secondary"
                onClick={() => onAction({ type: "end_turn" })}
                disabled={icarusArming || Boolean(diePick)}
              >
                End without scoring
              </button>
              {icarusArming && (
                <button
                  type="button"
                  className="secondary"
                  onClick={() => setIcarusArming(false)}
                >
                  Cancel Icarus
                </button>
              )}
              {diePick && (
                <button
                  type="button"
                  className="secondary"
                  onClick={() => setDiePick(null)}
                >
                  Cancel {label(diePick.cardId)}
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
          <div
            className={`dice-tray ${
              icarusArming || diePick ? "targeting" : ""
            }`}
          >
            {sortedDice.map(({ value, index, locked }) => {
              const psychicFace = match.psychic_previews?.[String(index)];
              const picked = diePick?.picked.includes(index);
              return (
                <button
                  key={index}
                  type="button"
                  className={`die ${locked ? "locked" : ""} ${
                    icarusArming || diePick ? "targetable" : ""
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
              {diePick
                ? `Pick ${2 - diePick.picked.length} more die(s) for ${label(diePick.cardId)}`
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
          <div className="card-tray power-tray">
            <span className="tray-label">Power</span>
            <div className="fan">
              {powerCards.length === 0 && (
                <span className="empty-fan muted">Empty</span>
              )}
              {powerCards.map((card, i) => (
                <Tip
                  key={`p-${card.id}-${i}`}
                  text={tipText(card.id, card.transparent)}
                >
                  <button
                    type="button"
                    className={`fan-card power ${
                      card.id === "icarus" && icarusArming ? "armed" : ""
                    }`}
                    disabled={!active || (card.id === "icarus" && !match.dice)}
                    onClick={() => castPower(card)}
                    style={{ zIndex: i + 1 }}
                  >
                    {label(card.id)}
                  </button>
                </Tip>
              ))}
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
                {hindranceCards.map((card, i) => (
                  <Tip key={`h-${card.id}-${i}`} text={tipText(card.id, card.transparent)}>
                    <button
                      type="button"
                      className="fan-card hindrance"
                      disabled={!hindranceTarget}
                      onClick={() => castHindrance(card)}
                    >
                      {label(card.id)}
                    </button>
                  </Tip>
                ))}
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
                ACTIVATABLE_TRADING.has(card.id) ? (
                  <Tip
                    key={`t-${card.id}-${i}`}
                    text={tipText(
                      card.id,
                      false,
                      card.id === "gambler"
                        ? `Cost ${me?.gambler_cost ?? 200} chips.`
                        : card.id === "lawyer" && (me?.lawyer_cooldown ?? 0) > 0
                          ? `Cooldown: ${me?.lawyer_cooldown} turns.`
                          : undefined,
                    )}
                  >
                    <button
                      type="button"
                      className={`fan-card trading ${
                        diePick?.cardId === card.id ? "armed" : ""
                      }`}
                      style={{ zIndex: i + 1 }}
                      disabled={tradingDisabled(card)}
                      onClick={() => activateTrading(card)}
                    >
                      {tradingLabel(card)}
                    </button>
                  </Tip>
                ) : (
                  <Tip key={`t-${card.id}-${i}`} text={tipText(card.id)}>
                    <div
                      className="fan-card trading passive"
                      style={{ zIndex: i + 1 }}
                    >
                      {tradingLabel(card)}
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

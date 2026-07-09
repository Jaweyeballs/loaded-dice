import { useMemo, useState } from "react";
import type { MatchState, PlayerState, RoomState } from "./types";

type Props = {
  room: RoomState;
  playerName: string;
  onAction: (action: Record<string, unknown>) => void;
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

function label(id: string): string {
  return id.replace(/_/g, " ");
}

export function GameView({ room, playerName, onAction }: Props) {
  const match = room.match as MatchState;
  const me = match.players.find((p) => p.name === playerName);
  const active = Boolean(match.you_are_active);
  const canShop = Boolean(match.you_can_use_shop);
  const [hindranceTarget, setHindranceTarget] = useState(
    () => match.players.find((p) => p.name !== playerName)?.name ?? "",
  );
  const [selectedSheet, setSelectedSheet] = useState(playerName);

  const sheetPlayer = useMemo(
    () => match.players.find((p) => p.name === selectedSheet) ?? match.players[0],
    [match.players, selectedSheet],
  );

  return (
    <div className="game">
      <header className="game-banner">
        <div>
          <strong>Loaded Dice</strong>
          <span className="muted"> · Room {room.room_code}</span>
        </div>
        <div>
          Rotation {match.rotation_count} · Phase: {label(match.phase)}
        </div>
        <div className={active ? "you-active" : "spectating"}>
          {match.is_over
            ? `Match over — winner: ${match.winner ?? "?"}`
            : active
              ? "Your turn"
              : `${match.active_player}'s turn — spectating`}
        </div>
      </header>

      <div className="game-grid">
        <section className="panel">
          <h2>Dice</h2>
          {match.dice ? (
            <>
              <div className="dice-row">
                {match.dice.values.map((value, index) => {
                  const locked = match.dice!.locked[index];
                  return (
                    <button
                      key={index}
                      type="button"
                      className={`die ${locked ? "locked" : ""}`}
                      disabled={!active}
                      onClick={() =>
                        onAction({
                          type: locked ? "unlock" : "lock",
                          index,
                        })
                      }
                    >
                      {value}
                    </button>
                  );
                })}
              </div>
              <p className="hint">
                Rolls {match.dice.rolls_this_turn}/{match.dice.max_rolls}
                {!active && " · click disabled while spectating"}
              </p>
              <div className="row">
                {match.phase === "between_turns" && active && (
                  <button type="button" onClick={() => onAction({ type: "start_turn" })}>
                    Start turn
                  </button>
                )}
                {match.phase === "turn_start" && active && (
                  <button
                    type="button"
                    onClick={() => onAction({ type: "begin_rolling" })}
                  >
                    Begin rolling
                  </button>
                )}
                {match.phase === "turn_active" && active && (
                  <>
                    <button type="button" onClick={() => onAction({ type: "roll" })}>
                      Roll
                    </button>
                    <button
                      type="button"
                      className="secondary"
                      onClick={() => onAction({ type: "end_turn" })}
                    >
                      End without scoring
                    </button>
                  </>
                )}
              </div>
            </>
          ) : (
            <div className="row">
              {match.phase === "between_turns" && active && !match.is_over && (
                <button type="button" onClick={() => onAction({ type: "start_turn" })}>
                  Start turn
                </button>
              )}
              {!active && <p className="hint">Waiting for {match.active_player}…</p>}
            </div>
          )}
        </section>

        {match.phase === "turn_start" && me && me.queued_hindrances.length > 0 && (
          <section className="panel warn">
            <h2>Hindrances on you</h2>
            <ul>
              {me.queued_hindrances.map((h, index) => (
                <li key={`${h.card_id}-${index}`}>
                  {label(h.card_id)} from {h.caster_name}
                  {active && (
                    <button
                      type="button"
                      className="inline"
                      onClick={() =>
                        onAction({ type: "block_hindrance", hindrance_index: index })
                      }
                    >
                      Parry
                    </button>
                  )}
                </li>
              ))}
            </ul>
            {active && !me.parry_ready && !me.power_cards.some((c) => c.id === "parry") && (
              <p className="hint">No Parry available — begin rolling to accept effects.</p>
            )}
          </section>
        )}

        <section className="panel">
          <h2>Your cards</h2>
          {!me ? (
            <p className="hint">Not seated</p>
          ) : (
            <>
              <div className="card-list">
                {me.power_cards.filter((c) => !HINDRANCE_IDS.has(c.id)).length === 0 && (
                  <span className="muted">No positive power cards</span>
                )}
                {me.power_cards
                  .filter((c) => !HINDRANCE_IDS.has(c.id))
                  .map((card, i) => (
                    <button
                      key={`${card.id}-${i}`}
                      type="button"
                      disabled={!active}
                      onClick={() => {
                        if (card.id === "icarus") {
                          const dieIndex = window.prompt("Die index to bump (0–4)", "0");
                          if (dieIndex == null) return;
                          onAction({
                            type: "cast_power",
                            card_id: card.id,
                            die_index: Number(dieIndex),
                          });
                          return;
                        }
                        onAction({ type: "cast_power", card_id: card.id });
                      }}
                    >
                      {label(card.id)}
                      {card.transparent ? " *" : ""}
                    </button>
                  ))}
              </div>
              <h3>Hindrances</h3>
              <div className="row wrap">
                <select
                  value={hindranceTarget}
                  onChange={(e) => setHindranceTarget(e.target.value)}
                  disabled={!active}
                >
                  {match.players
                    .filter((p) => p.name !== playerName)
                    .map((p) => (
                      <option key={p.name} value={p.name}>
                        {p.name}
                      </option>
                    ))}
                </select>
                {me.power_cards
                  .filter((c) => HINDRANCE_IDS.has(c.id))
                  .map((card, i) => (
                    <button
                      key={`h-${card.id}-${i}`}
                      type="button"
                      disabled={!active || !hindranceTarget}
                      onClick={() =>
                        onAction({
                          type: "cast_hindrance",
                          card_id: card.id,
                          target: hindranceTarget,
                        })
                      }
                    >
                      Cast {label(card.id)}
                    </button>
                  ))}
              </div>
              {me.trading_cards.length > 0 && (
                <p className="hint">
                  Trading: {me.trading_cards.map((c) => label(c.id)).join(", ")}
                </p>
              )}
            </>
          )}
        </section>

        <section className="panel">
          <h2>Shop {canShop ? "" : "(closed for you)"}</h2>
          <ul className="shop-list">
            {match.shop.stock.map((offer) => (
              <li key={offer.index}>
                <span>
                  {label(offer.card_id)} — {offer.price} chips
                </span>
                <button
                  type="button"
                  disabled={!canShop}
                  onClick={() =>
                    onAction({ type: "buy", stock_index: offer.index })
                  }
                >
                  Buy
                </button>
              </li>
            ))}
          </ul>
          <button
            type="button"
            className="secondary"
            disabled={!canShop}
            onClick={() => onAction({ type: "reroll_shop" })}
          >
            Reroll ({match.shop.reroll_cost} chips)
          </button>
        </section>

        <section className="panel wide">
          <div className="row wrap">
            <h2>Scoresheets</h2>
            <select
              value={selectedSheet}
              onChange={(e) => setSelectedSheet(e.target.value)}
            >
              {match.players.map((p) => (
                <option key={p.name} value={p.name}>
                  {p.name} ({p.total_score} pts, {p.chips} chips)
                </option>
              ))}
            </select>
          </div>
          <ScoreSheetTable
            player={sheetPlayer}
            previews={
              sheetPlayer.name === match.active_player ? match.previews : null
            }
            canScore={active && sheetPlayer.name === playerName}
            onScore={(category) => onAction({ type: "score", category })}
          />
        </section>

        <section className="panel wide">
          <h2>Standings</h2>
          <ul className="standings">
            {[...match.players]
              .sort((a, b) => b.total_score - a.total_score)
              .map((p) => (
                <li key={p.name}>
                  <strong>{p.name}</strong> {p.total_score} pts · {p.chips} chips
                  {p.name === match.active_player ? " · playing" : ""}
                </li>
              ))}
          </ul>
        </section>
      </div>
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
          <th>Preview</th>
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

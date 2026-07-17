/** Shared card ability blurbs for inventory, shop, and debuff hover tips. */

export const CARD_BLURBS: Record<string, string> = {
  merchant: "Earn 200 chips at the start of your turn (passive).",
  persuader: "+3 points on every scored hand (passive).",
  gecko: "+100 chips to all compensation payouts (passive).",
  gambler: "Pay chips for an extra reroll; cost rises by 100 each use.",
  lawyer: "End your turn without scoring (2-turn cooldown).",
  toddler: "Pick 2 dice for an extra reroll (only those dice roll).",
  psychic: "Pick 2 dice to preview their next rolled faces.",
  guardian: "Block a queued hindrance at turn start (1-turn cooldown).",
  forecaster: "On your turn, see hindrance cards held by other players (passive).",
  icarus: "Bump one die face up by 1 (wraps 6 → 1).",
  parry: "Block a single queued hindrance at turn start (consumable).",
  glass_half_full: "Target’s upper-section score is 0 this turn.",
  glass_half_empty: "Target’s lower-section score is 0 this turn.",
  positive_reinforcement:
    "If you attacked no one last rotation, +8 on this scored hand.",
  negative_reinforcement:
    "If you attacked no one last rotation, gain a transparent Parry.",
  positive_punishment:
    "If the target attacked you last rotation, −5 on their next scored hand.",
  negative_punishment:
    "If the target attacked you last rotation, they lose 200 chips.",
};

export function cardBlurb(cardId: string): string {
  return CARD_BLURBS[cardId] ?? "Ability description coming soon.";
}

export function cardTipLabel(cardId: string, transparent = false): string {
  const name = cardId.replace(/_/g, " ");
  return transparent ? `${name} (transparent)` : name;
}

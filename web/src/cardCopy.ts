/** Shared card ability blurbs for inventory, shop, and debuff hover tips. */

export const CARD_BLURBS: Record<string, string> = {
  merchant: "Earn 200 chips at the start of your turn (passive).",
  persuader: "+3 points on every scored hand (passive).",
  gecko: "+100 chips to all compensation payouts (passive).",
  gambler: "Pay chips for an extra reroll; cost rises by 100 each use.",
  lawyer: "End your turn without scoring (2-turn cooldown).",
  toddler: "Pick 2 dice to immediately reroll them (once per turn).",
  psychic: "Pick 2 dice to preview their next rolled faces (once per turn).",
  guardian: "Block a queued hindrance anytime before it resolves (1-turn cooldown).",
  forecaster: "On your turn, see hindrance cards held by other players (passive).",
  icarus: "Bump one die face up by 1 (wraps 6 → 1).",
  super_serum: "Increase every die by 1 (6s stay 6 — no wrap).",
  do_over:
    "Overwrite your last scored category with this hand’s score there. Full house / 4oak / straights: +5 only if this hand also qualifies (else 0). Use the scoresheet button — cannot overwrite Yahtzee.",
  benchwarmer: "Add an extra die (faces 1–3). Pick 5 dice when scoring.",
  helping_hand:
    "Take 400 chips or +10 on this hand; the other goes to a chosen player.",
  twins: "Link 2 dice; on the next roll the 2nd copies the 1st. Click again to cancel. Consumed when the link is rolled.",
  space_die: "Set one die to any face it can show.",
  boolean: "Add a 6/blank die for the rest of this turn. Pick 5 when scoring.",
  write_off: "End your turn without scoring.",
  parry: "Block a single queued hindrance anytime before it resolves (consumable).",
  glass_half_full: "Target’s upper-section score is 0 this turn.",
  glass_half_empty: "Target’s lower-section score is 0 this turn.",
  positive_reinforcement:
    "If you attacked no one last rotation, +8 on this scored hand.",
  negative_reinforcement:
    "If you attacked no one last rotation, gain a transparent Parry.",
  positive_punishment:
    "If the target attacked you last rotation, −5 on their next scored hand (stays until they score).",
  negative_punishment:
    "If the target attacked you last rotation, they lose 200 chips at their Start Turn (else keeps waiting).",
  blue_shell: "Queued on current 1st place; they lose 10 points on their Start Turn.",
  already_in_jail:
    "Stays until the target’s first lock; that die cannot be unlocked (blockable until then).",
};

export function cardBlurb(cardId: string): string {
  return CARD_BLURBS[cardId] ?? "Ability description coming soon.";
}

export function cardTipLabel(cardId: string, transparent = false): string {
  const name = cardId.replace(/_/g, " ");
  return transparent ? `${name} (transparent)` : name;
}

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
  forecaster:
    "On Start Turn, peek at others’ hindrance cards until your next Start Turn (new buys stay hidden).",
  icarus: "After rolling: bump one die up within its faces (standard wraps 6 → 1).",
  super_serum: "After rolling: raise every die by 1 within its faces (no wrap).",
  do_over:
    "Overwrite your last scored category with this hand’s score there. Full house / 4oak / straights: +5 only if this hand also qualifies (else 0). Use the scoresheet button — cannot overwrite Yahtzee.",
  benchwarmer: "Add an extra die (faces 1–3). Scoring uses the best 5 automatically.",
  helping_hand:
    "Take 400 chips or +10 on this hand; the other goes to a chosen player.",
  twins:
    "Link 2 dice; on the next roll the 2nd copies the 1st. Click again to cancel. Consumed when the link is rolled.",
  space_die: "After rolling: pick a die, then set it to any face it can show.",
  boolean: "Add a 6/blank die for the rest of this turn. Scoring uses the best 5 automatically.",
  write_off: "End your turn without scoring.",
  parry: "Block a single queued hindrance anytime before it resolves (consumable).",
  glass_half_full: "Target’s upper-section score is 0 this turn.",
  glass_half_empty: "Target’s lower-section score is 0 this turn.",
  positive_reinforcement:
    "If you attacked no one last rotation, +8 when you score (auto; not consumed on Write Off).",
  negative_reinforcement:
    "If you attacked no one last rotation, gain a transparent Parry when you score (auto).",
  positive_punishment:
    "If the target attacked anyone last rotation, −5 on their next scored hand (stays until they score).",
  negative_punishment:
    "If the target attacked anyone last rotation, they lose 200 chips at their Start Turn (else keeps waiting).",
  blue_shell:
    "Queued on the highest other player at cast; they lose 10 points on their Start Turn.",
  already_in_jail:
    "Stays until the target’s first lock; that die cannot be unlocked or have its face changed (blockable until then).",
  smoke_bomb:
    "At Start Turn: after their first roll, 2 random unlocked dice are force-locked and cannot be unlocked or have faces changed (blockable).",
  tax_audit:
    "At Start Turn: take up to 150 chips from the target (paid to you).",
  bounty_notice:
    "Mark a player; the next hindrance cast on them pays that caster 300 chips (then clears).",
  mixup:
    "Hindrances you cast cannot be blocked by Parry (Guardian still works).",
};

/** Second-person blurbs when a hindrance is on *you* (Debuffs tray). */
export const CARD_BLURBS_ON_YOU: Record<string, string> = {
  glass_half_full: "Your upper-section score is 0 this turn.",
  glass_half_empty: "Your lower-section score is 0 this turn.",
  positive_punishment:
    "If you attacked anyone last rotation, −5 on your next scored hand (stays until you score).",
  negative_punishment:
    "If you attacked anyone last rotation, you lose 200 chips at Start Turn (else it keeps waiting).",
  blue_shell: "You lose 10 points at your Start Turn.",
  already_in_jail:
    "On your first lock this turn, that die stays locked and its face cannot change (blockable until then).",
  smoke_bomb:
    "After your first roll this turn, 2 random unlocked dice are force-locked — you cannot unlock them or change their faces (blockable beforehand).",
  tax_audit: "At Start Turn you lose up to 150 chips (paid to the caster).",
  bounty_notice:
    "You are marked: the next hindrance cast on you pays that caster 300 chips (then clears).",
};

export function cardBlurb(cardId: string): string {
  return CARD_BLURBS[cardId] ?? "Ability description coming soon.";
}

/** Description for a hindrance sitting on the viewing player. */
export function cardBlurbOnYou(cardId: string): string {
  return CARD_BLURBS_ON_YOU[cardId] ?? cardBlurb(cardId);
}

export function cardTipLabel(cardId: string, transparent = false): string {
  const name = cardId.replace(/_/g, " ");
  return transparent ? `${name} (transparent)` : name;
}

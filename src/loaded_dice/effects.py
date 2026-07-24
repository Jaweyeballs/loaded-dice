"""Turn-scoped score modifiers — shared by preview and committed scoring."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class TurnEffects:
    """Modifiers active on a player for the current turn."""

    zero_upper: bool = False
    zero_lower: bool = False
    score_bonus: int = 0
    score_penalty: int = 0
    # Portion of score_bonus from Helping Hand (for HUD labeling).
    helping_hand_bonus: int = 0

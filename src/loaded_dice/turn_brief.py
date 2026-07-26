"""Turn preview brief sheets shown as HUD overlays."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class BriefAmountLine:
    amount: int
    label: str

    def to_dict(self) -> dict[str, Any]:
        return {"amount": self.amount, "label": self.label}


@dataclass
class TurnBrief:
    """A player-facing summary of what matters going into a turn."""

    kind: str  # "preview"
    version: int
    debuffs: list[str] = field(default_factory=list)
    chips: list[BriefAmountLine] = field(default_factory=list)
    buffs: list[str] = field(default_factory=list)
    scores: list[BriefAmountLine] = field(default_factory=list)
    net_chips: int = 0
    net_score: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "kind": self.kind,
            "version": self.version,
            "debuffs": list(self.debuffs),
            "chips": [line.to_dict() for line in self.chips],
            "buffs": list(self.buffs),
            "scores": [line.to_dict() for line in self.scores],
            "net_chips": self.net_chips,
            "net_score": self.net_score,
        }


def card_display_name(card_id: str) -> str:
    return card_id.replace("_", " ")

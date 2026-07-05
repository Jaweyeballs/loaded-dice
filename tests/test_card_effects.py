from loaded_dice.card_effects.negative_power import resolve_hindrance
from loaded_dice.cards import CardId
from loaded_dice.effects import TurnEffects
from loaded_dice.match import Match


def test_hindrance_resolver_sets_turn_effects():
    match = Match(["Alice", "Bob"])
    target = match.players[0]
    caster = match.players[1]
    target.turn_effects = TurnEffects()

    resolve_hindrance(CardId.GLASS_HALF_FULL, target, caster, match)
    assert target.turn_effects.zero_upper is True
    assert target.turn_effects.zero_lower is False

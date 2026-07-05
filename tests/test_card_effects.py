from loaded_dice.card_effects.negative_power import resolve_hindrance
from loaded_dice.card_effects.positive_power import cast_positive_power
from loaded_dice.cards import Card, CardId, CardKind
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


def test_parry_cast_sets_parry_ready():
    match = Match(["Alice"])
    player = match.players[0]
    player.inventory.add_power(Card(CardId.PARRY, CardKind.POWER))
    match.start_turn()
    match.begin_rolling()
    cast_positive_power(CardId.PARRY, player, match)
    assert player.parry_ready is True

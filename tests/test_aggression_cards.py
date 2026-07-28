"""New aggression-leaning power and trading cards."""

import pytest

from loaded_dice.card_effects.negative_power import (
    BOUNTY_NOTICE_REWARD,
    SMOKE_BOMB_LOCK_COUNT,
    TAX_AUDIT_CHIP_LOSS,
)
from loaded_dice.cards import CardId, card_for_id
from loaded_dice.economy import COMPENSATION_CHIPS_PER_ATTACKER
from loaded_dice.match import Match, WrongPhaseError


def _begin(match: Match) -> None:
    match.start_turn()


def test_smoke_bomb_locks_two_dice_after_first_roll():
    match = Match(["Alice", "Bob"])
    alice, bob = match.players
    alice.inventory.add_power(card_for_id(CardId.SMOKE_BOMB))
    _begin(match)
    match.roll()
    match.cast_hindrance(CardId.SMOKE_BOMB, bob)
    match.end_turn_without_scoring()
    _begin(match)
    assert bob.turn_effects.smoke_bomb_locks == SMOKE_BOMB_LOCK_COUNT
    assert len(bob.queued_hindrances) == 1
    assert bob.queued_hindrances[0].active is True
    match.roll()
    locked = sum(1 for die in match.dice.dice if die.locked)
    assert locked == SMOKE_BOMB_LOCK_COUNT
    assert bob.turn_effects.smoke_bomb_locks == 0
    assert len(bob.smoke_bomb_locked_indices) == SMOKE_BOMB_LOCK_COUNT
    assert all(match.dice.dice[i].locked for i in bob.smoke_bomb_locked_indices)
    match.end_turn_without_scoring()
    assert bob.queued_hindrances == []


def test_smoke_bomb_blocks_unlock_and_face_changing_effects():
    match = Match(["Alice", "Bob"])
    alice, bob = match.players
    alice.inventory.add_power(card_for_id(CardId.SMOKE_BOMB))
    _begin(match)
    match.roll()
    match.cast_hindrance(CardId.SMOKE_BOMB, bob)
    match.end_turn_without_scoring()
    _begin(match)
    match.roll()
    smoked = list(bob.smoke_bomb_locked_indices)
    assert len(smoked) == SMOKE_BOMB_LOCK_COUNT
    target = smoked[0]
    free = next(i for i in range(5) if i not in smoked)
    face = match.dice.dice[target].value

    with pytest.raises(WrongPhaseError, match="smoke"):
        match.unlock(target)
    assert match.dice.dice[target].locked is True
    assert match.dice.dice[target].value == face

    bob.inventory.add_power(card_for_id(CardId.ICARUS))
    with pytest.raises(WrongPhaseError, match="smoke"):
        match.cast_power_card(CardId.ICARUS, die_index=target)
    assert match.dice.dice[target].value == face

    bob.inventory.add_power(card_for_id(CardId.SPACE_DIE))
    with pytest.raises(WrongPhaseError, match="smoke"):
        match.cast_power_card(CardId.SPACE_DIE, die_index=target, face_value=6)
    assert match.dice.dice[target].value == face

    bob.inventory.add_power(card_for_id(CardId.SUPER_SERUM))
    match.cast_power_card(CardId.SUPER_SERUM)
    assert match.dice.dice[target].value == face

    bob.inventory.add_trading(card_for_id(CardId.TODDLER))
    with pytest.raises(WrongPhaseError, match="smoke"):
        match.activate_trading_card(CardId.TODDLER, die_indices=[target, free])
    assert match.dice.dice[target].value == face

    bob.inventory.add_trading(card_for_id(CardId.PSYCHIC))
    with pytest.raises(WrongPhaseError, match="smoke"):
        match.activate_trading_card(CardId.PSYCHIC, die_indices=[target, free])
    assert match.dice.dice[target].value == face


def test_tax_audit_transfers_chips_to_caster():
    match = Match(["Alice", "Bob"])
    alice, bob = match.players
    bob.chips = 500
    alice.chips = 100
    alice.inventory.add_power(card_for_id(CardId.TAX_AUDIT))
    _begin(match)
    match.roll()
    match.cast_hindrance(CardId.TAX_AUDIT, bob)
    match.end_turn_without_scoring()
    _begin(match)
    # Bob also earns per-attacker compensation for Alice's tax cast.
    assert bob.chips == 500 - TAX_AUDIT_CHIP_LOSS + COMPENSATION_CHIPS_PER_ATTACKER
    assert alice.chips == 100 + TAX_AUDIT_CHIP_LOSS
    assert alice.offturn_chip_events[-1].amount == TAX_AUDIT_CHIP_LOSS


def test_bounty_notice_pays_next_caster():
    match = Match(["Alice", "Bob", "Carol"])
    alice, bob, carol = match.players
    alice.inventory.add_power(card_for_id(CardId.BOUNTY_NOTICE))
    carol.inventory.add_power(card_for_id(CardId.GLASS_HALF_FULL))
    carol.chips = 50
    _begin(match)
    match.roll()
    match.cast_hindrance(CardId.BOUNTY_NOTICE, bob)
    assert any(h.card_id == CardId.BOUNTY_NOTICE for h in bob.queued_hindrances)
    match.end_turn_without_scoring()
    _begin(match)  # Bob
    match.end_turn_without_scoring()
    _begin(match)  # Carol
    match.roll()
    before = carol.chips
    match.cast_hindrance(CardId.GLASS_HALF_FULL, bob)
    assert carol.chips == before + BOUNTY_NOTICE_REWARD
    assert not any(h.card_id == CardId.BOUNTY_NOTICE for h in bob.queued_hindrances)
    assert any(h.card_id == CardId.GLASS_HALF_FULL for h in bob.queued_hindrances)


def test_bounty_notice_does_not_pay_when_placing_itself():
    match = Match(["Alice", "Bob"])
    alice, bob = match.players
    alice.chips = 10
    alice.inventory.add_power(card_for_id(CardId.BOUNTY_NOTICE))
    alice.inventory.add_power(card_for_id(CardId.BOUNTY_NOTICE))
    _begin(match)
    match.roll()
    match.cast_hindrance(CardId.BOUNTY_NOTICE, bob)
    match.cast_hindrance(CardId.BOUNTY_NOTICE, bob)
    assert alice.chips == 10
    assert sum(1 for h in bob.queued_hindrances if h.card_id == CardId.BOUNTY_NOTICE) == 2


def test_mixup_blocks_parry_but_allows_guardian():
    match = Match(["Alice", "Bob"])
    alice, bob = match.players
    alice.inventory.add_trading(card_for_id(CardId.MIXUP))
    alice.inventory.add_power(card_for_id(CardId.SMOKE_BOMB))
    bob.inventory.add_trading(card_for_id(CardId.GUARDIAN))
    bob.inventory.add_power(card_for_id(CardId.PARRY))
    _begin(match)
    match.roll()
    match.cast_hindrance(CardId.SMOKE_BOMB, bob)
    match.end_turn_without_scoring()
    with pytest.raises(WrongPhaseError, match="Mixup"):
        match.block_hindrance(0, CardId.PARRY, player=bob)
    match.block_hindrance(0, CardId.GUARDIAN, player=bob)
    assert bob.queued_hindrances == []

# Loaded Dice — Design Document

*Working title. Currency figures, point values, and slot counts throughout are placeholder/ballpark — not final balance. "Chips" are currency; "$" is shorthand for chip values for simplicity and to express relative value between cards.*

---

## 1. Theme

- Default theme: **casino**. Chips, slot-machine shop, high-denomination currency framing.
- **Roblox port**: re-skin away from casino theme for platform content guidelines. Core systems (currency, cards, characters) should stay theme-agnostic in code so the skin can be swapped without touching logic.

---

## 2. Currency & Economy

- Currency: **chips**, given in multiple ways (open system — see below).
- Shop: a slot-machine-style shop, available to a player during *other* players' turns (i.e. browsing/spending isn't limited to your own turn).
- **Compensation** (passive income mechanic). The two components **stack** — a player who attacked no one and was attacked by N people gets $2 + $1×N on their turn.
  - $1 per person who attacked you in the previous rotation
  - $2 if you did not attack anyone in the previous rotation
- **Base income**: scored hands and unspent rerolls both grant chips by default. Exact amounts TBD during balancing.
- Needs a full **rarity + economy system** for cards (drop rates, shop pricing tiers) — not yet designed.

---

## 3. Characters

Permanent boosts with drawbacks, picked at the start of a run/match.

| Character | Boost | Drawback |
|---|---|---|
| **Vampire** | Gain $2 per person you attack | Gains no compensation |
| **Hoarder** | Can hold an extra trading card | Cannot sell any trading cards |
| **Quantum cat** | Once per turn, change a single die's value up or down by one | One less power card slot |
| **Miscounter** | +2 to all scored hands | Can only hit Yahtzee once per game |
| **Cyclops** | Can hit Yahtzee with only 4 dice | One less trading card slot |

- Note: drawbacks of **Miscounter** and **Cyclops** may be swapped — open balance question, not finalized.

---

## 4. Card System Rules

### Definitions
- **Rotation**: one full cycle in which every player has taken a turn.
- **Attack**: triggered by casting any negative power card, regardless of whether it has a chosen target or resolves on whoever it happens to hit (e.g. Blue Shell counts as an attack even though the caster doesn't choose the target).
- **Base slot counts**: power card hand size is **5**; trading card slots is **3**. Both are modifiable by character effects (Quantum Cat, Cyclops, Hoarder).
- **Dice locking**: standard Yahtzee keep/reroll — players lock dice between rerolls. (Relevant to Already in Jail, below.)
- **Rolls per turn**: default **3** (initial roll + up to 2 rerolls). Card effects (e.g. The Gambler, The Toddler) may increase this limit for a turn.
- **Scoring hand**: always exactly **5 dice** chosen from whatever dice are in play. Extra dice from card effects (e.g. Benchwarmer, The Coin) are rolled **alongside** normal dice on the same rolls. If more than 5 dice are showing when the player scores, they must **select which 5** to use before picking a category.

### Rules
- **Power cards** = consumables, mostly single-use.
  - **Positive** power cards take effect **immediately**.
  - **Negative** power cards take effect **on the target's turn**.
- **Trading cards** = persistent modifiers that stay in effect as long as they're in your party.
- **Transparent power cards**: trait of power cards, makes them not take up a slot in inventory. can be randomly spawned or given (e.g. Negative Reinforcement). Do **not** consume a power card slot.

### Turn flow
1. **Turn start (active player)** — Queued hindrances are shown with their caster. Effects are displayed but do **not** resolve yet; the player may respond first (e.g. Parry, Guardian). Clicking **Start Turn** resolves them — targeted hindrances apply as specified; untargeted ones (e.g. Blue Shell) take effect at this moment (e.g. −10 points).
2. **Active phase** — Standard Yahtzee: roll, lock, reroll, score. Extra dice from active effects roll with the normal dice. When scoring, if more than 5 dice are in play, the player is prompted to select 5 for their scoring hand, then pick a category. The active player may play positive power cards and cast hindrances on chosen targets at any point. Only the active player may cast cards.
3. **End turn** — Clicking **End Turn** passes play. The player who just finished may now open the shop (browse, buy, reroll stock) and spectate until their next turn. Shop access closes when they click **Start Turn** and reopens on their next **End Turn**. Players cannot cast cards when it is not their turn.

---

## 5. Power Cards (Consumables)

### Positive (benefit self)
| Name | Effect |
|---|---|
| Icarus | Choose a die and increase its value, wrapping 6 → 1 |
| Super serum | Increase entire hand's value by 1 |
| Do over | If this hand matches your last *scored* hand (and isn't Yahtzee), overwrite that score with this one |
| Parry | Block a single hindrance cast on you this turn |
| Positive reinforcement | If you attacked no one last rotation, gain 8 points on this scored hand |
| Negative reinforcement | If you attacked no one last rotation, gain a *transparent* Parry |
| Benchwarmer | Roll an extra die alongside normal dice this roll (limited to values 1–3); select 5 dice for scoring |
| Helping hand | Choose: gain $4, or gain 10 points on this hand — whichever you don't pick goes to another player of your choice |
| The twins | Two of your dice on the next roll are guaranteed to match (can't be used on two dice that already differ in a way that conflicts) |
| Space die | Choose a die and set it to any value it could show |
| The coin | Roll an extra die alongside normal dice for the rest of the round (3 six-faces, 3 blank/0 faces); select 5 dice for scoring |
| Write off | End this turn without scoring a hand |

### Negative (hinder another player)
| Name | Effect |
|---|---|
| Positive punishment | If the target attacked you last round, they lose 5 points on their next scored hand |
| Negative punishment | If the target attacked you last round, they lose $2 |
| Blue shell | The player in 1st place loses 10 points |
| Already in jail | The first die the target locks on their turn cannot be unlocked for the rest of their turn |
| Glass half empty | Any lower-section hand picked this round scores 0 |
| Glass half full | Any upper-section hand picked this round scores 0 |

- **Glass half empty** and **Glass half full** cannot both be active on the same player at the same time.

---

## 6. Trading Cards

| Name | Effect |
|---|---|
| The gecko | +$1 to all compensation payouts |
| The toddler | Choose 2 dice to use in an extra reroll |
| The persuader | +3 points on every scored hand |
| The gambler | Pay $2 for an extra reroll; cost increases by $1 each time used |
| The psychic | Choose 2 dice to preview their next rolled value |
| The guardian | Parries a hindrance card of your choice; goes on cooldown for one turn after triggering |
| The forecaster | Reveals all hindrance cards held by all players, visible only to you, on your turn |
| The merchant | Earn $2 on your turn |
| The lawyer | End your turn without scoring a hand (2-turn cooldown) |

---

## 7. Open Questions / Deferred

Everything blocking M0–M2 has been resolved (see Definitions in §4 and updated Currency rules in §2). These two are pure balance decisions — not blocking, to be tested and adjusted once the game is playable:

1. **Miscounter/Cyclops drawback swap** — test during balancing.
2. **Rarity + economy system** — needed before shop pricing/drop rates can be implemented, but not before M0.

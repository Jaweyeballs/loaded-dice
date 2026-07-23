# Loaded Dice — Design Document

*Working title. Chip amounts, point values, and slot counts throughout are placeholder/ballpark — not final balance.*

---

## 1. Theme

- Default theme: **casino**. Chips, slot-machine shop, high-denomination currency framing.
- **Roblox port**: re-skin away from casino theme for platform content guidelines. Core systems (currency, cards, characters) should stay theme-agnostic in code so the skin can be swapped without touching logic.

---

## 2. Currency & Economy

- Currency: **chips**, given in multiple ways (open system — see below).
- Shop: a slot-machine-style shop, available to a player during *other* players' turns (i.e. browsing/spending isn't limited to your own turn).
- **Compensation** (passive income mechanic). The two components **stack** — a player who attacked no one and was attacked by N people gets **200 + 100×N** chips on their turn.
  - **100** chips per person who attacked you in the previous rotation
  - **200** chips if you did not attack anyone in the previous rotation
- **Base income**: scoring a hand grants **300** chips; each unused standard reroll (of the default 3) grants **150** chips when you score — ability-granted extra rerolls do not. **Interest**: at turn start, earn **50** chips per **200** chips held (max **200** interest per turn).
- Needs a full **rarity + economy system** for cards (drop rates, shop pricing tiers) — not yet designed.

---

## 3. Characters

Permanent boosts with drawbacks, picked at the start of a run/match.

| Character | Boost | Drawback |
|---|---|---|
| **Vampire** | Gain **200** chips per person you attack | Gains no compensation |
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
| Do over | Overwrite your last scored category with this hand’s score in that box (no matching-hand requirement). **+5** if that category was full house, four of a kind, large straight, or small straight. Cannot overwrite a scored Yahtzee. If the current hand is a Yahtzee and Yahtzee is already filled, Do over does nothing — score the extra Yahtzee normally. Use the scoresheet Do over control (not cast-from-card matching). |
| Parry | Block a single hindrance cast on you this turn |
| Positive reinforcement | If you attacked no one last rotation, gain 8 points on this scored hand |
| Negative reinforcement | If you attacked no one last rotation, gain a *transparent* Parry |
| Benchwarmer | Roll an extra die alongside normal dice this roll (limited to values 1–3); select 5 dice for scoring |
| Helping hand | Choose: gain **400** chips, or gain 10 points on this hand — whichever you don't pick goes to another player of your choice |
| Twins | Choose 2 dice; the second rolls the same value as the first on the next roll |
| Space die | Choose a die and set it to any value it could show |
| Boolean | Roll an extra die alongside normal dice for the rest of the round (3 six-faces, 3 blank/0 faces); select 5 dice for scoring |
| Write off | End this turn without scoring a hand |

### Negative (hinder another player)
| Name | Effect |
|---|---|
| Positive punishment | If the target attacked you last round, they lose 5 points on their next scored hand |
| Negative punishment | If the target attacked you last round, they lose **200** chips |
| Blue shell | The player in 1st place loses 10 points |
| Already in jail | The first die the target locks on their turn cannot be unlocked for the rest of their turn |
| Glass half empty | Any lower-section hand picked this round scores 0 |
| Glass half full | Any upper-section hand picked this round scores 0 |

- **Glass half empty** and **Glass half full** cannot both be active on the same player at the same time.

---

## 6. Trading Cards

| Name | Effect |
|---|---|
| The gecko | +**100** chips to all compensation payouts |
| The toddler | Choose 2 dice to use in an extra reroll |
| The persuader | +3 points on every scored hand |
| The gambler | Pay **200** chips for an extra reroll; cost increases by **100** chips each time used |
| The psychic | Choose 2 dice to preview their next rolled value |
| The guardian | Parries a hindrance card of your choice; goes on cooldown for one turn after triggering |
| The forecaster | Reveals all hindrance cards held by all players, visible only to you, on your turn |
| The merchant | Earn **200** chips on your turn |
| The lawyer | End your turn without scoring a hand (2-turn cooldown) |

---

## 7. In-Match HUD (browser)

Reference mock: [`docs/ui-refs/hud.jpg`](ui-refs/hud.jpg). The play surface is a **table**; HUD chrome peeks onto it and can be pulled in or pushed aside for clutter control.

### Collapsible chrome
- **Left panel** (Debuffs + Leaderboard tabs), **top-right scoresheet**, and **power / trading card trays** each have a control (button or arrow) to slide further onto the HUD or mostly off-screen so only a peek remains on the table edge.
- Power and trading cards may **overlap slightly**, but each card must stay readable at a glance. Exact spacing need not match the mock.

### Scoresheet (top right)
- Modes: **Mine** (viewer’s sheet) and **Current player** (live sheet of whoever’s turn it is).
- **Mine** is a dropdown listing every player in the lobby; selecting a name shows that player’s live scoresheet.
- A **fullscreen** control expands the scoresheet so it can be read without scrolling.

### Left panel — Debuffs
- Shows hindrances / debuffs on **the viewing player**.
- Updates live when new ones are cast; entries clear after the turn on which they take effect has finished.

### Left panel — Leaderboard
- Placement list of all lobby players with **current chips** and **scoresheet totals**.
- Next to each score: a **+/−** live **net score change** heading into the next rotation.
- An **up/down arrow** indicates predicted placement rise or fall next rotation.
- **Ranking order only updates at the end of each rotation** (after every player’s turn has settled — scoring, power-ups, and debuffs). Mid-rotation the list order stays fixed even as chips/scores change.
- Clicking a **name** on the leaderboard switches the top-right scoresheet to that player’s live sheet (same as picking them from the Mine dropdown).

### Cards & shop
- Hovering a **power card**, **trading card**, or **debuff** shows its description (copy TBD).
- The **shop sign** is visible and usable when it is **not** your turn; it is **hidden during your turn**.

### Dice
- Dice always show the **active player’s** live rolls and locks (spectators see the same).
- After a roll, dice **sort into ascending face order** in the tray above the power cards, where they can be locked.

---

## 8. Open Questions / Deferred

Everything blocking M0–M2 has been resolved (see Definitions in §4 and updated Currency rules in §2). These are pure balance / later-product decisions — not blocking:

1. **Miscounter/Cyclops drawback swap** — test during balancing.
2. **Rarity + economy system** — needed before shop pricing/drop rates can be implemented, but not before M0.
3. **QoL / deep customizability** — intentional product pillar; specifics deferred until the core HUD loop is solid.

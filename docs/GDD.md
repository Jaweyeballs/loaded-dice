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
- **Rolls per turn**: default **3** (initial roll + up to 2 rerolls). Card effects (e.g. The Gambler) may increase this limit for a turn.
- **Scoring hand**: always exactly **5 dice** chosen from whatever dice are in play. Extra dice from card effects (e.g. Benchwarmer, The Coin) are rolled **alongside** normal dice on the same rolls. If more than 5 dice are showing when the player scores, they must **select which 5** to use before picking a category.

### Rules
- **Power cards** = consumables, mostly single-use.
  - **Positive** power cards take effect **immediately**.
  - **Negative** power cards take effect **on the target's turn**.
- **Trading cards** = persistent modifiers that stay in effect as long as they're in your party.
- **Transparent power cards**: trait of power cards, makes them not take up a base inventory slot (they expand capacity instead — e.g. **6/6** with five normal + one transparent). Can be randomly spawned or given (e.g. Negative Reinforcement). Selling a transparent card yields **double** its shop price.
- **Inventory Use / Sell**: Clicking a held card opens **Use** (green) and/or **Sell** (red). Sell is always available and pays shop price − **100** (floor **0**), or 2× shop price if transparent. Use appears only on manually played cards; it is grayed out when the card cannot be used right now. Do over uses the scoresheet control instead of Use. Passives and reinforcements have Sell only.

### Turn flow
1. **Start turn (active player)** — Clicking **Start Turn** pays interest/compensation, then resolves **ready** queued hindrances for this trigger (Glass half, Blue Shell, and punishments whose attack condition is met). Play goes straight to the active/rolling phase. Unresolved hindrances (e.g. Already in Jail, or punishments waiting on their condition) stay queued across turns. Players may **block** any still-queued hindrance on themselves (Parry, Guardian) at any time before that card resolves.
2. **Active phase** — Standard Yahtzee: roll, lock, reroll, score. Extra dice from active effects roll with the normal dice. When scoring with more than 5 dice, the best 5-die combination for the chosen category is used automatically (same as the scoresheet preview). The active player may play positive power cards and cast hindrances on chosen targets at any point. Only the active player may cast cards. **Already in Jail** resolves on the first lock of a turn (one queued copy per lock) and can still be blocked before that lock. Once jailed, that die’s face is immutable for the rest of the turn.
3. **End turn** — Clicking **End Turn** passes play. The player who just finished may now open the shop (browse, buy, reroll stock) and spectate until their next turn. Shop access closes when they click **Start Turn** and reopens on their next **End Turn**. Players cannot cast cards when it is not their turn.

---

## 5. Power Cards (Consumables)

### Positive (benefit self)
| Name | Effect |
|---|---|
| Space die | After the first roll: choose a die, then set it to any face that die can show (1–6, or 0/6 for Boolean, 1–3 for Benchwarmer, etc.) |
| Icarus | After the first roll: choose a die and increase its value within its face set (standard wraps 6 → 1) |
| Super serum | After the first roll: increase every die by 1 within its face set (top face stays put — no wrap) |
| Do over | Overwrite your last scored category with this hand’s score in that box. For full house / four of a kind / large or small straight: **+5** only if this hand also qualifies for a non-zero score in that box; otherwise the overwrite is **0**. Cannot overwrite a scored Yahtzee. If the current hand is a Yahtzee and Yahtzee is already filled, Do over does nothing — score the extra Yahtzee normally. Use the scoresheet Do over control (no Use button on the card). |
| Parry | Block a single unresolved hindrance queued on you (any time before it resolves) |
| Positive reinforcement | If you attacked no one last rotation, gain 8 points when you **score** a hand (consumed on that score; kept if you Write Off / end without scoring). No Use button. |
| Negative reinforcement | If you attacked no one last rotation, gain a *transparent* Parry when you **score** a hand (consumed on that score). No Use button. |
| Benchwarmer | Roll an extra die alongside normal dice this roll (limited to values 1–3); scoring auto-picks the best 5 |
| Helping hand | Choose: gain **400** chips, or gain 10 points on this hand — whichever you don't pick goes to another player of your choice |
| Twins | Link 2 dice (1st = source). On the next roll involving that link, the 2nd copies the 1st. Click the card again to cancel. Consumed only when the link resolves on a roll (including Toddler). |
| Boolean | Roll an extra die alongside normal dice for the rest of the round (3 six-faces, 3 blank/0 faces); scoring auto-picks the best 5 |
| Write off | End this turn without scoring a hand |

### Negative (hinder another player)
| Name | Effect |
|---|---|
| Positive punishment | If the target attacked **anyone** last rotation, arm −5 that applies on their **next scored hand** (survives Write Off). If the attack condition is not met at Start Turn, the card stays queued. |
| Negative punishment | If the target attacked **anyone** last rotation, they lose **200** chips at Start Turn. If not, the card stays queued until a later Start Turn where the condition is true. |
| Blue shell | Queued on the highest-standing player **other than you** at cast time; that player loses 10 points on their next Start Turn (does not retarget if standings change). |
| Already in jail | Stays queued until the target’s **first lock** on a turn (or blocked). That die cannot be unlocked for the rest of the turn, and its face value cannot change under any effect (Icarus, Super Serum, Space Die, Toddler, Psychic, Twins, etc.). Each lock consumes one queued copy. |
| Smoke bomb | At Start Turn: after the target’s **first roll**, **2** random unlocked dice are force-locked (blockable beforehand). |
| Tax audit | At Start Turn: take up to **150** chips from the target (paid to the caster). |
| Bounty notice | Marks the target; the **next** hindrance cast on them pays that caster **300** chips, then the notice clears (placing Bounty itself does not pay out). |
| Glass half empty | At Start Turn: any lower-section hand scored this turn is 0 (resolves for the turn regardless of which half they score). |
| Glass half full | At Start Turn: any upper-section hand scored this turn is 0 (resolves for the turn regardless of which half they score). |

- **Glass half empty** and **Glass half full** cannot both be active on the same player at the same time.
- **Debuff fan linger**: while a hindrance is still affecting you, it stays in your Debuffs tray (marked ACTIVE) so you can re-read it on hover — including future cards. Instant one-shots (e.g. Blue Shell / Tax Audit chip or point loss already applied) leave immediately. Turn-scoped effects clear at end of turn (and on score when relevant); armed cross-turn effects (e.g. Positive punishment) stay until scored or blocked. Blocked cards always leave (and undo an already-applied linger effect when needed).

---

## 6. Trading Cards

| Name | Effect |
|---|---|
| The gecko | +**100** chips to all compensation payouts |
| The toddler | Choose 2 dice to immediately reroll them (once per turn) |
| The persuader | +3 points on every scored hand |
| The gambler | Pay **200** chips for an extra reroll; cost increases by **100** chips each time used |
| The psychic | Choose 2 dice to preview their next rolled value (once per turn) |
| The guardian | Block an unresolved queued hindrance of your choice; goes on cooldown for one turn after triggering |
| The forecaster | On your **Start Turn**, reveals other players’ held hindrance cards under their hidden hands (visible only to you until your next Start Turn). New buys mid-cycle stay hidden; used cards drop out of the peek. Selling Forecaster clears the peek on your next Start Turn. |
| The mixup | Hindrances you cast cannot be blocked by **Parry** (Guardian still works). |
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

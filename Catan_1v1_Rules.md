# Settlers of Catan — 1v1 (Base Game) Rules Specification

Purpose: a precise, implementation-oriented ruleset for building a two-player
base-game Catan. No expansions (no Seafarers, Cities & Knights, etc.).

> Note: base Catan is officially 3–4 players. This spec adapts the standard
> rules to two players using conventions common to online 1v1 (e.g. colonist.io).
> Section 13 lists every place where a 1v1 design decision was made, so they can
> be changed to match a specific platform.

Resource naming (official / casual, used interchangeably here):
lumber = wood, brick = clay, wool = sheep, grain = wheat, ore = ore.

---

## 1. Components

Terrain hexes (19 total):
- 4 Forest  -> produce lumber (wood)
- 4 Pasture -> produce wool (sheep)
- 4 Fields  -> produce grain (wheat)
- 3 Hills   -> produce brick
- 3 Mountains -> produce ore
- 1 Desert  -> produces nothing; robber starts here

Number tokens (18 total, one per non-desert hex):
- Values: 2, 3, 3, 4, 4, 5, 5, 6, 6, 8, 8, 9, 9, 10, 10, 11, 11, 12
- There is no 7 token.
- 6 and 8 are the highest-probability numbers ("red numbers").

Harbors / ports (9 total, on the coast):
- 4 generic ports: trade any 1 resource type 3:1 with the bank
- 5 specific ports: 2:1 for a single resource (one each for lumber, brick,
  wool, grain, ore)

Resource card bank: 19 cards of each of the 5 resources (95 total).

Development cards (25 total, shuffled into a face-down deck):
- 14 Knight
- 5 Victory Point
- 2 Road Building
- 2 Year of Plenty
- 2 Monopoly

Per-player pieces (each of the 2 players):
- 5 settlements
- 4 cities
- 15 roads

Special award cards: Longest Road, Largest Army.
Other: 2 six-sided dice, 1 robber.

---

## 2. The Board

The board is a hexagon made of the 19 terrain hexes, surrounded by coastline
containing the 9 ports.

Board coordinates:
- Each hex has 6 corners (vertices) and 6 edges.
- Vertices are shared between up to 3 hexes; edges between up to 2 hexes.
- Settlements and cities occupy vertices. Roads occupy edges.

Setup of the board (random generation):
1. Randomly place the 19 terrain hexes.
2. Place the robber on the desert.
3. Randomly assign the 18 number tokens to the 18 non-desert hexes.
4. Assign the 9 port types to the 9 coastal port locations. Port positions are
   fixed around the coast (see Section 13, decision D6, for exact-position vs.
   simplified placement).

Optional balancing constraint (Section 13, decision D5):
- The two 6s and two 8s ("red numbers") may not be placed on adjacent hexes.

---

## 3. Initial Placement (Setup Phase)

Turn order: determine a starting player (P1). P2 is the opponent. P1 takes the
first regular turn after setup.

Placement uses a snake draft over two rounds:
- Round 1 (forward): P1 places, then P2 places.
- Round 2 (reverse): P2 places, then P1 places.
- Net placement order: P1, P2, P2, P1.

On each placement, the active player:
1. Places 1 settlement on any unoccupied vertex that satisfies the distance
   rule (Section 8). During setup, settlements do NOT need to connect to a road.
2. Places 1 road on an edge adjacent to the settlement they just placed.

Starting resources:
- When a player places their SECOND settlement (their round-2 placement), they
  immediately draw 1 resource card for each resource-producing hex adjacent to
  that settlement. (A desert hex yields nothing.)
- The first settlement grants no resources.

After setup completes, play proceeds to P1's first turn.

---

## 4. Turn Sequence (Overview)

On a player's turn, in this order:
1. Optional: play 1 development card (may be done before rolling — see Section 10).
2. Roll the dice (Section 5). This is mandatory and happens exactly once.
3. Trade and build, in any order, repeated as desired (Sections 7 and 8).
4. End turn; pass to the opponent.

A player may play at most 1 development card total during their turn (Knight or
a progress card), and it may be played at any point in the turn, including
before the roll. Revealing Victory Point cards is not restricted (Section 10).

---

## 5. Rolling Dice & Resource Production

Roll 2 six-sided dice; sum them.

If the sum is 2–6 or 8–12:
- Every terrain hex whose number token equals the rolled sum produces its
  resource, EXCEPT a hex currently occupied by the robber, which produces
  nothing.
- For each producing hex, every player who has a building on one of that hex's
  6 corner vertices receives resources from the bank:
  - settlement -> 1 card of that resource
  - city       -> 2 cards of that resource
- A single roll can produce from multiple hexes and multiple resource types.
- A player benefits from every one of their buildings adjacent to a producing
  hex (a city adjacent to two triggered hexes collects from both).

Bank shortage rule:
- If the bank does not have enough cards of a resource type to pay everyone
  entitled to it this roll:
  - If only ONE player is entitled to that resource, that player takes as many
    as remain in the bank.
  - If MORE THAN ONE player is entitled and there are not enough for all, NO
    player receives any of that resource this roll.
  - (Applies independently per resource type.)

If the sum is 7: resolve the robber (Section 6). No resources are produced.

---

## 6. The Robber and Rolling a 7

When a 7 is rolled:
1. Discard step: every player (both) holding MORE THAN 9 resource cards
   (i.e. 10+) must discard half of their hand, rounded down. The player chooses
   which cards to discard.
   (1v1 deviation from base Catan's 7-card limit — see Section 13, decision D2.)
2. Move step: the player who rolled the 7 moves the robber to any land hex
   other than the one it currently occupies. The robber must be moved.
3. Steal step: after moving, the roller steals 1 random resource card from a
   player who has a settlement or city on a corner of the robber's new hex.
   - In 1v1 the only possible target is the opponent.
   - If the opponent has a building on that hex and at least 1 resource card,
     take 1 card at random from their hand.
   - If the opponent has no building there or no cards, no card is stolen.

The robber's effect persists: while it sits on a hex, that hex produces no
resources on future rolls until the robber is moved again (via a 7 or a Knight).

### 6.1 Friendly Robber (1v1 rule — not in base Catan)

The robber may NOT be moved to a hex whose adjacent opponent building(s) all
belong to a player whose VISIBLE victory-point total is 2 or fewer. This
protects a trailing player from being robber-locked early. Applies to both the
7-roll move and the Knight-card move.

- "Visible VP" = settlements + cities + Longest Road + Largest Army. It
  EXCLUDES hidden Victory Point development cards (those are not public and so
  cannot gate a public rule).
- A hex is "protected" only if EVERY opponent building on it belongs to a
  player at or under the 2-visible-VP threshold. If any building on that hex
  belongs to a player above the threshold, the hex is a legal destination and
  the steal resolves normally against eligible players there. In 1v1 there is
  exactly one opponent, so a hex with that opponent's building is protected iff
  that opponent's visible VP <= 2.
- Hexes with no opponent building (empty, or only the mover's own buildings,
  or the desert) are always legal destinations — the robber can be moved there
  to block production even though no steal occurs.
- Enforced as a legality constraint on move-robber actions in legal_actions()
  (and on Knight-card robber moves), NOT as a post-hoc check.
- A legal destination always exists (the desert / own-only / empty hexes), so
  the "robber must move" requirement can never deadlock.
- See Section 13, decision D9.

---

## 7. Trading

Trading happens only on the active player's turn, after rolling. Trading and
building may be interleaved freely.

Maritime (bank) trade — no opponent needed:
- Default rate: give 4 identical resource cards, receive 1 resource of choice.
- Generic port (3:1): if the player has a settlement/city on a generic port
  vertex, they may trade any 3 identical cards for 1 of choice.
- Specific port (2:1): if the player has a settlement/city on that resource's
  port vertex, they may trade 2 of that resource for 1 of choice.
- The best available rate for the given resource applies. You cannot receive
  the same resource you gave.

Domestic (player) trade:
- The active player may propose a trade of resource cards with the opponent.
- Both parties must agree. Only resource cards may be traded (no dev cards, no
  pieces). A trade must involve at least 1 card each way; you cannot "gift".
- (Player trading is a 1v1 decision — see Section 13, decision D1.)

---

## 8. Building

Costs:
- Road:        1 lumber + 1 brick
- Settlement:  1 lumber + 1 brick + 1 wool + 1 grain
- City:        3 ore + 2 grain  (replaces one of your existing settlements)
- Development card: 1 ore + 1 wool + 1 grain

Supply limits (per player): 15 roads, 5 settlements, 4 cities. A player cannot
build a piece they have none of remaining in supply.

Road placement:
- Must be on an empty edge.
- Must connect to the player's own network: adjacent to one of that player's
  roads, settlements, or cities.
- A road may not extend through a vertex occupied by an OPPONENT's settlement or
  city for the purpose of connectivity (an opponent building blocks road
  continuation past that vertex — relevant to Longest Road, Section 11).

Settlement placement (after setup):
- Must be on an empty vertex.
- Distance rule: no adjacent vertex (one connected by a single edge) may contain
  any settlement or city (yours or the opponent's).
- Must connect to at least one of the player's own roads.
- Placing a settlement grants no immediate resources (unlike setup round 2).

City placement:
- Upgrades one of the player's existing settlements on the board.
- The settlement piece is returned to that player's supply (freeing a settlement
  slot), and a city piece is placed on that vertex.

Buying a development card:
- Pay the cost; draw the top card of the shuffled dev deck; keep it hidden.
- If the dev deck is empty, dev cards can no longer be bought.

---

## 9. (reserved)

---

## 10. Development Cards

General rules:
- A player may play at most 1 development card per turn (a Knight OR a progress
  card). It may be played at any time during the turn, including before rolling.
- A development card CANNOT be played on the same turn it was purchased.
  (Exception: Victory Point cards, see below.)

Card types:

Knight:
- Move the robber to any land hex other than its current one, then steal 1
  random card from an opponent adjacent to that hex (identical to the 7's move +
  steal, but with no dice roll and no discard step).
- Each Knight played increases the player's "army size" by 1 (relevant to
  Largest Army, Section 11). Played Knight cards stay face-up in front of the
  player.

Progress cards:
- Road Building: place 2 roads for free, following normal road placement rules.
  If only one legal placement exists, place 1; if none, place 0. Placed roads
  count against the 15-road supply.
- Year of Plenty: take any 2 resource cards from the bank (any combination).
  If the bank cannot provide 2, take what is available.
- Monopoly: name 1 resource type. The opponent must give the player ALL of their
  cards of that resource.

Victory Point cards (5 total):
- Each is worth 1 victory point.
- They are kept hidden and count toward the holder's VP total continuously.
- Revealing them does not count as the player's 1 dev-card play. In practice
  they are only revealed when doing so brings the player to 10+ VP to win
  (Section 12).

---

## 11. Longest Road and Largest Army

Longest Road (worth 2 VP):
- Awarded to the first player to build a single continuous road of length 5 or
  more (5+ connected road segments in one unbranched path).
- "Continuous" = a path of connected edges. Branches do not add to the length;
  the longest single path is what counts.
- An opponent's settlement or city placed on a vertex along a road path breaks
  the path at that vertex (the two sides are counted separately).
- Once held, it transfers to the opponent only if the opponent builds a road
  strictly LONGER than the current holder's longest road. On an exact tie, the
  current holder keeps it.
- If the holder's longest road drops below 5 (e.g., broken by an opponent) and
  no one else has 5+, the card is set aside (held by no one). If it drops below
  5 but the opponent has 5+, the opponent takes it.

Largest Army (worth 2 VP):
- Awarded to the first player to have played 3 or more Knight cards.
- Transfers to the opponent only if the opponent has played strictly MORE
  Knights than the current holder. On a tie, the current holder keeps it.

---

## 12. Winning

- A player wins immediately upon reaching 15 or more victory points DURING THEIR
  OWN TURN. They may reveal hidden Victory Point cards at that moment to reach
  the threshold and declare victory.
  (1v1 target of 15, not the base-game 10 — see Section 13, decision D8.
  Buildings alone cap at 13 VP, so reaching 15 requires Longest Road, Largest
  Army, and/or Victory Point dev cards.)
- Victory points come from:
  - Settlement: 1 each
  - City: 2 each
  - Longest Road card: 2
  - Largest Army card: 2
  - Victory Point development cards: 1 each
- A player cannot win on the opponent's turn (e.g., if a card transfer during
  the opponent's turn would put them at 10). Victory is only checked/declared on
  the holder's own turn.

---

## 13. 1v1 Design Decisions to Confirm

These have no universal standard for two-player base Catan. Defaults below match
common online 1v1 (colonist.io-style). Adjust to match your target exactly.

- D1. Player (domestic) trading: DEFAULT = allowed (Section 7). Some 1v1
  variants disable it. Decide whether the two players can negotiate trades.
- D2. Robber discard threshold: THIS PROJECT = discard half (rounded down) when
  holding 10+ cards (i.e. more than 9), a 1v1 deviation from the base 8+ rule
  (Section 6, step 1).
- D3. Bank size: DEFAULT = finite, 19 per resource, with the shortage rule
  (Section 5). Some digital games treat the bank as effectively unlimited.
  Decide whether to enforce bank limits.
- D4. Development deck size/composition: DEFAULT = standard 25-card deck
  (Section 1). Confirm you are not using a reduced deck for 1v1.
- D5. Red-number adjacency: DEFAULT = enforce that 6s and 8s are never adjacent
  during board generation. Can be disabled for fully random boards.
- D6. Port placement: DEFAULT = 9 ports at fixed standard coastal positions with
  types shuffled. Simplification: assign ports to any coastal vertices. Decide
  how faithful port geometry must be.
- D7. Optional "neutral player" variant: some 2-player house rules add a third
  set of blocking pieces or trade limits to reduce runaway leads. DEFAULT =
  none (pure standard rules with 2 players). Include only if desired.
- D8. Winning VP total: THIS PROJECT = 15 (a 1v1 deviation from the base 10),
  per Section 12. Buildings cap at 13, so a Longest Road / Largest Army / VP
  dev-card source is required for any game to terminate.
- D9. Friendly robber: THIS PROJECT = enabled (Section 6.1). The robber cannot
  be moved onto a hex whose only adjacent opponent buildings belong to a player
  with <= 2 visible VP. Not a base-game rule; can be disabled to match a
  platform without it.

---

## 14. Edge Cases and Clarifications

- Rolling is mandatory and occurs exactly once per turn (after any pre-roll dev
  card).
- The robber must always be moved to a different hex on a 7 or Knight; it may be
  placed on the desert or any land hex.
- A player may choose to move the robber to a hex where the opponent has no
  building (resulting in no steal) — e.g., to block a valuable hex.
- Resources are drawn from and returned to a shared bank; discards, steals via
  Monopoly, and trades move cards between hands, not to the bank (except
  maritime trades and Year of Plenty, which involve the bank).
- A city counts as 1 building on its vertex for adjacency/robber purposes but
  yields 2 resources on production.
- The distance rule always applies, including during setup.
- Only the active player may build or initiate trades, and only after rolling
  (dev cards excepted).
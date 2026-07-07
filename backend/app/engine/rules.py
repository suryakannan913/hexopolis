"""The 1v1 ruleset (CATAN_1V1_RULES.md) — single source of truth.

Interface shape follows the reusable-engine pattern from BOT_LOGIC_REFERENCE.md
(generate_playable_actions / apply_action / copy / terminal check):

    state = new_game(("P1", "P2"), seed=42)
    for a in legal_actions(state): ...
    apply_action(state, a)            # mutates; simulate on state.copy()

All randomness (dice, deck order, board, robber steal) comes from state.rng,
so a seed + an action sequence fully reproduces a game.
"""
import random
from itertools import combinations_with_replacement
from typing import Dict, List, Optional, Tuple

from app.models.board import Board, Edge, HexCoord, Resource, Vertex
from app.engine.actions import Action, ActionType
from app.engine.board_gen import generate_board
from app.engine.state import (
    CITY,
    CITY_COST,
    DEV_CARD_COST,
    DEV_DECK_COMPOSITION,
    DISCARD_LIMIT,
    FRIENDLY_ROBBER_VISIBLE_VP,
    GameState,
    LARGEST_ARMY_MIN,
    LONGEST_ROAD_MIN,
    Phase,
    PlayerState,
    ROAD_COST,
    SETTLEMENT,
    SETTLEMENT_COST,
    SETUP_ORDER,
    WINNING_POINTS,
    DevCard,
    zero_devs,
)

RESOURCES = list(Resource)


def new_game(names: Tuple[str, str] = ("Player 1", "Player 2"), seed: Optional[int] = None) -> GameState:
    """Create a fresh game. seed=None draws one from the system (still stored,
    so any game remains reproducible after the fact)."""
    if seed is None:
        seed = random.SystemRandom().randrange(2**63)
    rng = random.Random(seed)
    board, desert, ports = generate_board(rng)
    deck = list(DEV_DECK_COMPOSITION)
    rng.shuffle(deck)
    players = [PlayerState(id=i, name=n) for i, n in enumerate(names)]
    return GameState(
        board=board, ports=ports, robber=desert, players=players,
        rng=rng, seed=seed, dev_deck=deck, current_player=SETUP_ORDER[0],
    )


# --------------------------------------------------------------------------
# geometry / affordability helpers
# --------------------------------------------------------------------------

def _vertices_adjacent(v1: Vertex, v2: Vertex) -> bool:
    """Two corners are adjacent iff they share exactly 2 hex coords."""
    return len(set(v1.hex_coords) & set(v2.hex_coords)) == 2


def _distance_ok(state: GameState, v: Vertex) -> bool:
    """§8 distance rule: no building on v or any adjacent vertex (always applies)."""
    return v not in state.buildings and all(
        not _vertices_adjacent(v, w) for w in state.buildings
    )


def _setup_settlement_vertices(state: GameState) -> List[Vertex]:
    return [v for v in state.board.get_all_vertices() if _distance_ok(state, v)]


def _settlement_vertices(state: GameState, pid: int) -> List[Vertex]:
    """Normal play adds the road-connection requirement (§8)."""
    return [
        v for v in _setup_settlement_vertices(state)
        if any(state.roads.get(e) == pid for e in state.board.get_edges_for_vertex(v))
    ]


def _road_edges(state: GameState, pid: int) -> List[Edge]:
    """§8 road placement: empty board edge connected to the player's network.
    An opponent's building on a shared vertex blocks continuation through it."""
    out = []
    for e in state.board.get_all_edges():
        if e in state.roads:
            continue
        for v in state.board.get_edge_endpoints(e):
            b = state.buildings.get(v)
            if b is not None:
                if b[0] == pid:
                    out.append(e)
                    break
                continue  # opponent building: cannot connect through this vertex
            if any(f != e and state.roads.get(f) == pid
                   for f in state.board.get_edges_for_vertex(v)):
                out.append(e)
                break
    return out


def _can_afford(p: PlayerState, cost: Dict[Resource, int]) -> bool:
    return all(p.resources[r] >= n for r, n in cost.items())


def _pay(state: GameState, p: PlayerState, cost: Dict[Resource, int]) -> None:
    """Building costs return to the bank (§14)."""
    for r, n in cost.items():
        p.resources[r] -= n
        state.bank[r] += n


def _grant(state: GameState, p: PlayerState, r: Resource, n: int = 1) -> None:
    """Give from the bank, capped by what the bank has (D3)."""
    take = min(n, state.bank[r])
    state.bank[r] -= take
    p.resources[r] += take


def trade_rate(state: GameState, pid: int, give: Resource) -> int:
    """§7: best of 2:1 specific port, 3:1 generic port, 4:1 default."""
    rate = 4
    for v, (owner, _) in state.buildings.items():
        if owner != pid or v not in state.ports:
            continue
        port = state.ports[v]
        if port == give:
            return 2
        if port is None:
            rate = min(rate, 3)
    return rate


def _playable_dev(state: GameState, p: PlayerState, card: DevCard) -> bool:
    """§10: max 1 dev play per turn; a card can't be played the turn it was bought."""
    if state.dev_played_this_turn:
        return False
    return p.dev_hand[card] - p.dev_bought_this_turn[card] >= 1


def _yop_values(state: GameState) -> List[tuple]:
    """§10 Year of Plenty: any 2 from the bank; if the bank can't provide 2,
    take what is available (1 or 0)."""
    total = sum(state.bank.values())
    if total == 0:
        return [()]
    if total == 1:
        return [(r,) for r in RESOURCES if state.bank[r] > 0]
    vals = []
    for r1, r2 in combinations_with_replacement(RESOURCES, 2):
        need2 = 2 if r1 == r2 else 1
        if state.bank[r1] >= need2 and state.bank[r2] >= 1:
            vals.append((r1, r2))
    return vals


def _robber_destinations(state: GameState, mover: int) -> List[HexCoord]:
    """§6: must move to a different land hex. §6.1 friendly robber: a hex is
    off-limits iff it has opponent buildings and ALL their owners sit at or
    under the visible-VP threshold."""
    dests = []
    for coord in state.board.hexes:
        if coord == state.robber:
            continue
        owners = {
            state.buildings[v][0]
            for v in state.board.get_vertices_for_hex(coord)
            if v in state.buildings and state.buildings[v][0] != mover
        }
        if owners and all(state.visible_vp(o) <= FRIENDLY_ROBBER_VISIBLE_VP for o in owners):
            continue
        dests.append(coord)
    return dests


# --------------------------------------------------------------------------
# legal move generation
# --------------------------------------------------------------------------

def legal_actions(state: GameState) -> List[Action]:
    """Exhaustive legal moves for whoever must decide next (state.actor())."""
    if state.phase == Phase.GAME_OVER:
        return []
    pid = state.actor()
    p = state.players[pid]

    if state.phase == Phase.SETUP_SETTLEMENT:
        return [Action(pid, ActionType.BUILD_SETTLEMENT, v)
                for v in _setup_settlement_vertices(state)]

    if state.phase == Phase.SETUP_ROAD:
        board_edges = state.board.get_all_edges()
        return [Action(pid, ActionType.BUILD_ROAD, e)
                for e in state.board.get_edges_for_vertex(state.setup_anchor)
                if e in board_edges and e not in state.roads]

    if state.phase == Phase.DISCARD:
        return [Action(pid, ActionType.DISCARD, r)
                for r in RESOURCES if p.resources[r] > 0]

    if state.phase == Phase.MOVE_ROBBER:
        return [Action(pid, ActionType.MOVE_ROBBER, c)
                for c in _robber_destinations(state, pid)]

    # MAIN phase
    if state.free_roads_pending > 0:  # committed Road Building placements
        return [Action(pid, ActionType.BUILD_ROAD, e) for e in _road_edges(state, pid)]

    acts: List[Action] = []
    # §4/§10: one dev card may be played at any point in the turn, incl. pre-roll
    if _playable_dev(state, p, DevCard.KNIGHT):
        acts.append(Action(pid, ActionType.PLAY_KNIGHT))
    if _playable_dev(state, p, DevCard.ROAD_BUILDING):
        acts.append(Action(pid, ActionType.PLAY_ROAD_BUILDING))
    if _playable_dev(state, p, DevCard.YEAR_OF_PLENTY):
        acts += [Action(pid, ActionType.PLAY_YEAR_OF_PLENTY, v) for v in _yop_values(state)]
    if _playable_dev(state, p, DevCard.MONOPOLY):
        acts += [Action(pid, ActionType.PLAY_MONOPOLY, r) for r in RESOURCES]

    if not state.has_rolled:
        # §4: rolling is mandatory; nothing else (but a dev play) before it
        return [Action(pid, ActionType.ROLL)] + acts

    if p.settlements_left > 0 and _can_afford(p, SETTLEMENT_COST):
        acts += [Action(pid, ActionType.BUILD_SETTLEMENT, v)
                 for v in _settlement_vertices(state, pid)]
    if p.roads_left > 0 and _can_afford(p, ROAD_COST):
        acts += [Action(pid, ActionType.BUILD_ROAD, e) for e in _road_edges(state, pid)]
    if p.cities_left > 0 and _can_afford(p, CITY_COST):
        acts += [Action(pid, ActionType.BUILD_CITY, v) for v in state.settlements_of(pid)]
    if state.dev_deck and _can_afford(p, DEV_CARD_COST):
        acts.append(Action(pid, ActionType.BUY_DEV_CARD))
    for give in RESOURCES:
        if p.resources[give] >= trade_rate(state, pid, give):
            acts += [Action(pid, ActionType.MARITIME_TRADE, (give, recv))
                     for recv in RESOURCES if recv != give and state.bank[recv] > 0]
    acts.append(Action(pid, ActionType.END_TURN))
    return acts


# --------------------------------------------------------------------------
# applying actions
# --------------------------------------------------------------------------

def apply_action(state: GameState, action: Action, validate: bool = True) -> GameState:
    """Mutate state by one action. validate=False skips the legality check for
    hot simulation loops that already draw from legal_actions()."""
    if state.phase == Phase.GAME_OVER:
        raise ValueError("game is over")
    if validate and action not in legal_actions(state):
        raise ValueError(f"illegal action: {action}")

    pid, t, v = action.player, action.type, action.value
    if t == ActionType.ROLL:
        _apply_roll(state)
    elif t == ActionType.DISCARD:
        _apply_discard(state, pid, v)
    elif t == ActionType.MOVE_ROBBER:
        _apply_move_robber(state, pid, v)
    elif t == ActionType.BUILD_SETTLEMENT:
        _apply_build_settlement(state, pid, v)
    elif t == ActionType.BUILD_ROAD:
        _apply_build_road(state, pid, v)
    elif t == ActionType.BUILD_CITY:
        _apply_build_city(state, pid, v)
    elif t == ActionType.BUY_DEV_CARD:
        _apply_buy_dev(state, pid)
    elif t == ActionType.PLAY_KNIGHT:
        _apply_play_knight(state, pid)
    elif t == ActionType.PLAY_ROAD_BUILDING:
        _apply_play_road_building(state, pid)
    elif t == ActionType.PLAY_YEAR_OF_PLENTY:
        _apply_play_yop(state, pid, v)
    elif t == ActionType.PLAY_MONOPOLY:
        _apply_play_monopoly(state, pid, v)
    elif t == ActionType.MARITIME_TRADE:
        _apply_maritime(state, pid, v)
    elif t == ActionType.END_TURN:
        _apply_end_turn(state)
    else:  # pragma: no cover
        raise ValueError(f"unknown action type: {t}")

    _check_win(state, pid)
    return state


def _apply_roll(state: GameState) -> None:
    d = (state.rng.randint(1, 6), state.rng.randint(1, 6))
    state.last_roll = d
    state.has_rolled = True
    if d[0] + d[1] == 7:
        for pl in state.players:  # §6 step 1 with the D2 threshold
            state.discard_quota[pl.id] = (
                pl.hand_size() // 2 if pl.hand_size() > DISCARD_LIMIT else 0
            )
        state.phase = Phase.DISCARD if any(state.discard_quota) else Phase.MOVE_ROBBER
    else:
        _produce(state, d[0] + d[1])


def _produce(state: GameState, number: int) -> None:
    """§5 production with the bank-shortage rule, independently per resource."""
    for r in RESOURCES:
        owed: Dict[int, int] = {}
        for h in state.board.get_hexes_by_dice_number(number):
            if h.resource != r or h.coord == state.robber:
                continue
            for vx in state.board.get_vertices_for_hex(h.coord):
                b = state.buildings.get(vx)
                if b is not None:
                    owed[b[0]] = owed.get(b[0], 0) + (2 if b[1] == CITY else 1)
        if not owed:
            continue
        if state.bank[r] >= sum(owed.values()):
            for o, n in owed.items():
                state.bank[r] -= n
                state.players[o].resources[r] += n
        elif len(owed) == 1:  # single entitled player takes what remains
            (o, n), = owed.items()
            _grant(state, state.players[o], r, n)
        # else: shortage with both entitled -> nobody receives this resource


def _apply_discard(state: GameState, pid: int, r: Resource) -> None:
    p = state.players[pid]
    p.resources[r] -= 1
    state.bank[r] += 1  # discards return to the bank (see rules-doc note on §14)
    state.discard_quota[pid] -= 1
    if not any(state.discard_quota):
        state.phase = Phase.MOVE_ROBBER  # mover is the roller (= current player)


def _apply_move_robber(state: GameState, pid: int, coord: HexCoord) -> None:
    state.robber = coord
    victims = sorted({
        state.buildings[vx][0]
        for vx in state.board.get_vertices_for_hex(coord)
        if vx in state.buildings and state.buildings[vx][0] != pid
    })
    victims = [o for o in victims if state.players[o].hand_size() > 0]
    if victims:
        victim = state.players[victims[0]]  # 1v1: at most one opponent
        pool = [r for r in RESOURCES for _ in range(victim.resources[r])]
        stolen = state.rng.choice(pool)
        victim.resources[stolen] -= 1
        state.players[pid].resources[stolen] += 1
    state.phase = Phase.MAIN  # has_rolled is preserved (a pre-roll Knight still must roll)


def _apply_build_settlement(state: GameState, pid: int, v: Vertex) -> None:
    p = state.players[pid]
    if state.phase == Phase.SETUP_SETTLEMENT:
        state.buildings[v] = (pid, SETTLEMENT)
        p.settlements_left -= 1
        if state.setup_index in (2, 3):  # §3: round-2 settlement grants resources
            for h in state.board.get_hexes_for_vertex(v):
                if h.resource is not None:
                    _grant(state, p, h.resource, 1)
        state.setup_anchor = v
        state.phase = Phase.SETUP_ROAD
        return
    _pay(state, p, SETTLEMENT_COST)
    state.buildings[v] = (pid, SETTLEMENT)
    p.settlements_left -= 1
    _maintain_longest_road(state, pid)  # §11: may break the opponent's road


def _apply_build_road(state: GameState, pid: int, e: Edge) -> None:
    p = state.players[pid]
    if state.phase == Phase.SETUP_ROAD:
        state.roads[e] = pid
        p.roads_left -= 1
        state.setup_anchor = None
        state.setup_index += 1
        if state.setup_index >= len(SETUP_ORDER):
            state.phase = Phase.MAIN
            state.current_player = 0
            state.turn_number = 1
        else:
            state.current_player = SETUP_ORDER[state.setup_index]
            state.phase = Phase.SETUP_SETTLEMENT
        return
    if state.free_roads_pending > 0:  # Road Building placements are free
        state.free_roads_pending -= 1
    else:
        _pay(state, p, ROAD_COST)
    state.roads[e] = pid
    p.roads_left -= 1
    if state.free_roads_pending > 0 and (p.roads_left == 0 or not _road_edges(state, pid)):
        state.free_roads_pending = 0  # §10: place fewer if fewer are legal
    _maintain_longest_road(state, pid)


def _apply_build_city(state: GameState, pid: int, v: Vertex) -> None:
    p = state.players[pid]
    _pay(state, p, CITY_COST)
    state.buildings[v] = (pid, CITY)
    p.settlements_left += 1  # §8: the settlement piece returns to supply
    p.cities_left -= 1


def _apply_buy_dev(state: GameState, pid: int) -> None:
    p = state.players[pid]
    _pay(state, p, DEV_CARD_COST)
    card = state.dev_deck.pop(0)
    p.dev_hand[card] += 1
    p.dev_bought_this_turn[card] += 1  # §10: not playable this turn (VP still count)


def _apply_play_knight(state: GameState, pid: int) -> None:
    p = state.players[pid]
    p.dev_hand[DevCard.KNIGHT] -= 1
    state.dev_played_this_turn = True
    p.knights_played += 1
    _maintain_largest_army(state, pid)
    state.phase = Phase.MOVE_ROBBER  # §10: move + steal, no dice, no discard step


def _apply_play_road_building(state: GameState, pid: int) -> None:
    p = state.players[pid]
    p.dev_hand[DevCard.ROAD_BUILDING] -= 1
    state.dev_played_this_turn = True
    n = min(2, p.roads_left)
    state.free_roads_pending = n if _road_edges(state, pid) else 0  # §10: 2/1/0


def _apply_play_yop(state: GameState, pid: int, value: tuple) -> None:
    p = state.players[pid]
    p.dev_hand[DevCard.YEAR_OF_PLENTY] -= 1
    state.dev_played_this_turn = True
    for r in value:
        _grant(state, p, r, 1)


def _apply_play_monopoly(state: GameState, pid: int, r: Resource) -> None:
    p = state.players[pid]
    p.dev_hand[DevCard.MONOPOLY] -= 1
    state.dev_played_this_turn = True
    opp = state.players[1 - pid]
    p.resources[r] += opp.resources[r]  # hand-to-hand, not via the bank (§14)
    opp.resources[r] = 0


def _apply_maritime(state: GameState, pid: int, value: Tuple[Resource, Resource]) -> None:
    give, recv = value
    p = state.players[pid]
    rate = trade_rate(state, pid, give)
    p.resources[give] -= rate
    state.bank[give] += rate
    state.bank[recv] -= 1
    p.resources[recv] += 1


def _apply_end_turn(state: GameState) -> None:
    p = state.players[state.current_player]
    p.dev_bought_this_turn = zero_devs()  # bought cards become playable next turn
    state.dev_played_this_turn = False
    state.has_rolled = False
    state.free_roads_pending = 0
    state.current_player = 1 - state.current_player
    state.turn_number += 1


# --------------------------------------------------------------------------
# Longest Road / Largest Army / winning
# --------------------------------------------------------------------------

def longest_road_length(state: GameState, pid: int) -> int:
    """§11: longest single continuous path of the player's roads (edge-simple);
    an opponent building on a vertex cuts the path there (may still end there)."""
    edges = state.roads_of(pid)
    if not edges:
        return 0
    board = state.board
    incident: Dict[Vertex, List[Edge]] = {}
    for e in edges:
        for vx in board.get_edge_endpoints(e):
            incident.setdefault(vx, []).append(e)
    blocked = {vx for vx, (o, _) in state.buildings.items() if o != pid}

    def dfs(vx: Vertex, used: frozenset) -> int:
        best = len(used)
        if vx in blocked and used:  # cannot continue through an enemy building
            return best
        for e in incident.get(vx, []):
            if e in used:
                continue
            w = next(x for x in board.get_edge_endpoints(e) if x != vx)
            best = max(best, dfs(w, used | {e}))
        return best

    return max(dfs(vx, frozenset()) for vx in incident)


def _maintain_longest_road(state: GameState, actor: int) -> None:
    """§11 award/transfer/set-aside logic; recomputed after any road or any
    settlement (a settlement can break the opponent's path)."""
    lengths = [longest_road_length(state, 0), longest_road_length(state, 1)]
    holder = state.longest_road_owner
    if holder is not None:
        other = 1 - holder
        if lengths[holder] < LONGEST_ROAD_MIN:
            state.longest_road_owner = other if lengths[other] >= LONGEST_ROAD_MIN else None
        elif lengths[other] > lengths[holder]:  # strictly longer; ties keep it
            state.longest_road_owner = other
    else:
        qualified = [i for i in (0, 1) if lengths[i] >= LONGEST_ROAD_MIN]
        if len(qualified) == 1:
            state.longest_road_owner = qualified[0]
        elif len(qualified) == 2:
            # Both qualify while the card is unheld (possible after a set-aside):
            # the acting player takes it unless strictly shorter.
            state.longest_road_owner = (
                actor if lengths[actor] >= lengths[1 - actor] else 1 - actor
            )


def _maintain_largest_army(state: GameState, actor: int) -> None:
    """§11: first to 3+ knights; transfers only on strictly more."""
    counts = [state.players[0].knights_played, state.players[1].knights_played]
    holder = state.largest_army_owner
    if holder is None:
        if counts[actor] >= LARGEST_ARMY_MIN:
            state.largest_army_owner = actor
    elif counts[1 - holder] > counts[holder]:
        state.largest_army_owner = 1 - holder


def _check_win(state: GameState, actor: int) -> None:
    """§12: win at 15+ total VP (hidden VP cards included), only on the
    winner's own turn — enforced by requiring actor == current_player."""
    if state.winner is None and actor == state.current_player \
            and state.total_vp(actor) >= WINNING_POINTS:
        state.winner = actor
        state.phase = Phase.GAME_OVER

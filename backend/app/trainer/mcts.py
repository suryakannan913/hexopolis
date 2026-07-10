"""Tier 2: UCB1 Monte Carlo Tree Search recommender.

Structure ported from catanatron's MCTSPlayer (BOT_LOGIC_REFERENCE.md §3.9):
select / expand / rollout / backpropagate with the UCB1 formula and
EXP_C = sqrt(2), leaf evaluation by rollout-to-end with the same
weighted-random policy as tier 1.

Documented deviations from the source (per the confirmed plan):
- Chance nodes by SAMPLING, not execute_spectrum: our apply_action resolves
  randomness internally via state.rng, so stochastic actions (roll, dev draw,
  robber steal) accumulate up to OUTCOME_SAMPLES sampled child states; once at
  the cap we reuse existing children uniformly (they are i.i.d. draws from the
  true outcome distribution). Deterministic actions keep a single child.
- num_simulations defaults to 200, not the source's 10, which its own doc
  flags as undersized; our engine plays full games in ~0.1s so the budget is
  affordable.
- Proper two-player UCT: selection at a node maximizes the NODE ACTOR's win
  rate (opponent nodes minimize ours). The source backpropagates and selects
  from self's perspective everywhere, implicitly assuming a cooperative
  opponent — a known weakness we do not copy.
"""
import math
import random
from typing import Dict, List, Optional

from app.engine import apply_action, legal_actions
from app.engine.actions import Action, ActionType
from app.engine.state import GameState
from app.trainer.recommend import PLY_CAP, Recommendation, rollout

EXP_C = 2 ** 0.5          # UCB1 exploration constant (catanatron MCTSPlayer)
NUM_SIMULATIONS = 200     # source default is 10; see module docstring
OUTCOME_SAMPLES = 8       # sampled-outcome cap per stochastic action

_STOCHASTIC = {ActionType.ROLL, ActionType.BUY_DEV_CARD, ActionType.MOVE_ROBBER}


class _Node:
    """One concrete (sampled) game state in the tree."""

    def __init__(self, state: GameState):
        self.state = state
        self.visits = 0
        self.actions: List[Action] = [] if state.is_terminal() else legal_actions(state)
        self.untried: List[Action] = list(self.actions)
        self.children: Dict[Action, List["_Node"]] = {a: [] for a in self.actions}
        # Aggregate per-action stats, always from the ADVISEE's perspective.
        self.a_visits: Dict[Action, int] = {a: 0 for a in self.actions}
        self.a_wins: Dict[Action, int] = {a: 0 for a in self.actions}


def _sample_child(node: _Node, action: Action, master: random.Random) -> _Node:
    """Apply `action` to a copy with a fresh RNG stream (one sampled outcome)."""
    child_state = node.state.copy()
    child_state.rng = random.Random(master.randrange(2**63))
    apply_action(child_state, action, validate=False)
    return _Node(child_state)


def _descend(node: _Node, action: Action, master: random.Random) -> _Node:
    """Pick the child to continue through: deterministic actions reuse their
    single child; stochastic ones sample new outcomes up to OUTCOME_SAMPLES."""
    kids = node.children[action]
    if not kids or (action.type in _STOCHASTIC and len(kids) < OUTCOME_SAMPLES):
        kids.append(_sample_child(node, action, master))
        return kids[-1]
    return master.choice(kids)


def _select_ucb(node: _Node, advisee: int, exploration: float) -> Action:
    """UCB1 from the node actor's perspective (opponent nodes minimize ours)."""
    from_advisee = node.state.actor() == advisee
    log_n = math.log(node.visits)

    def score(a: Action) -> float:
        mean = node.a_wins[a] / node.a_visits[a]
        if not from_advisee:
            mean = 1.0 - mean
        return mean + exploration * math.sqrt(log_n / node.a_visits[a])

    return max(node.actions, key=score)


def mcts_recommend(state: GameState, num_simulations: int = NUM_SIMULATIONS,
                   seed: Optional[int] = None, exploration: float = EXP_C,
                   ply_cap: int = PLY_CAP) -> List[Recommendation]:
    """Rank every legal action for state.actor() by MCTS-estimated win rate.

    Root actions never explored (possible only when num_simulations is smaller
    than the action count) report win_probability 0.0 with sims=0.
    """
    if state.is_terminal():
        raise ValueError("game is over — nothing to recommend")
    advisee = state.actor()
    master = random.Random(seed)
    root = _Node(state.copy())

    for _ in range(num_simulations):
        node, path = root, []

        # Select: descend fully-expanded nodes by UCB1.
        while not node.state.is_terminal() and not node.untried:
            action = _select_ucb(node, advisee, exploration)
            path.append((node, action))
            node = _descend(node, action, master)

        # Expand: try one untried action, then evaluate by rollout.
        if not node.state.is_terminal():
            action = node.untried.pop(master.randrange(len(node.untried)))
            path.append((node, action))
            node = _descend(node, action, master)

        if node.state.is_terminal():
            winner = node.state.winner
        else:
            playout = node.state.copy()
            rng = random.Random(master.randrange(2**63))
            playout.rng = rng
            winner = rollout(playout, rng, ply_cap)

        # Backpropagate from the advisee's perspective.
        won = 1 if winner == advisee else 0
        node.visits += 1
        for n, a in path:
            n.visits += 1
            n.a_visits[a] += 1
            n.a_wins[a] += won

    results = [
        Recommendation(
            a,
            root.a_wins[a] / root.a_visits[a] if root.a_visits[a] else 0.0,
            root.a_visits[a],
        )
        for a in root.actions
    ]
    results.sort(key=lambda r: r.win_probability, reverse=True)
    return results

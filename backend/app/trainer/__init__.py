"""1v1 Catan trainer — move recommendation with estimated win probabilities.

Built on the engine's reusable interface (legal_actions / apply_action /
GameState.copy / is_terminal), per BOT_LOGIC_REFERENCE.md §5. Two tiers:

    recommend(state, ...)        flat Monte Carlo (GreedyPlayoutsPlayer shape)
    mcts_recommend(state, ...)   UCB1 tree search  (MCTSPlayer shape)
    value_recommend(state, ...)  instant 1-ply value fn (ValueFunctionPlayer)

The Monte Carlo tiers rank every legal action by estimated win probability;
the value tier ranks by heuristic score (not a probability) in milliseconds.
"""
from app.trainer.recommend import Recommendation, recommend
from app.trainer.mcts import mcts_recommend
from app.trainer.value_function import (
    CONTENDER_WEIGHTS,
    DEFAULT_WEIGHTS,
    ScoredAction,
    value_fn,
    value_recommend,
)

__all__ = [
    "Recommendation", "recommend", "mcts_recommend",
    "ScoredAction", "value_fn", "value_recommend",
    "DEFAULT_WEIGHTS", "CONTENDER_WEIGHTS",
]

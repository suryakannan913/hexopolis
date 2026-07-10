"""1v1 Catan trainer — move recommendation with estimated win probabilities.

Built on the engine's reusable interface (legal_actions / apply_action /
GameState.copy / is_terminal), per BOT_LOGIC_REFERENCE.md §5. Two tiers:

    recommend(state, ...)            flat Monte Carlo (GreedyPlayoutsPlayer)
    mcts_recommend(state, ...)       UCB1 tree search (MCTSPlayer)
    value_recommend(state, ...)      instant 1-ply value fn (ValueFunctionPlayer)
    alphabeta_recommend(state, ...)  expectiminimax (AlphaBetaPlayer)

The Monte Carlo tiers rank every legal action by estimated win probability;
the value/alpha-beta tiers rank by heuristic score (not a probability).
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
from app.trainer.alphabeta import alphabeta_recommend

__all__ = [
    "Recommendation", "recommend", "mcts_recommend",
    "ScoredAction", "value_fn", "value_recommend", "alphabeta_recommend",
    "DEFAULT_WEIGHTS", "CONTENDER_WEIGHTS",
]

"""1v1 Catan trainer — move recommendation with estimated win probabilities.

Built on the engine's reusable interface (legal_actions / apply_action /
GameState.copy / is_terminal), per BOT_LOGIC_REFERENCE.md §5. Two tiers:

    recommend(state, ...)        flat Monte Carlo (GreedyPlayoutsPlayer shape)
    mcts_recommend(state, ...)   UCB1 tree search  (MCTSPlayer shape)

Both return the same thing: every legal action for the player to act, ranked
by estimated win probability, descending.
"""
from app.trainer.recommend import Recommendation, recommend
from app.trainer.mcts import mcts_recommend

__all__ = ["Recommendation", "recommend", "mcts_recommend"]

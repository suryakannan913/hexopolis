"""Headless 1v1 Catan engine — single source of truth for the ruleset.

Interface (the shape BOT_LOGIC_REFERENCE.md calls out as reusable):
    state  = new_game(names, seed)      # seedable, reproducible
    acts   = legal_actions(state)       # exhaustive legal moves for the actor
    apply_action(state, action)         # mutate state (bots copy() first)
    state.copy() / state.is_terminal() / state.winner
"""
from app.engine.actions import Action, ActionType
from app.engine.state import (
    CITY,
    SETTLEMENT,
    WINNING_POINTS,
    DevCard,
    GameState,
    Phase,
    PlayerState,
)
from app.engine.rules import apply_action, legal_actions, longest_road_length, new_game

__all__ = [
    "Action", "ActionType", "DevCard", "GameState", "Phase", "PlayerState",
    "SETTLEMENT", "CITY", "WINNING_POINTS",
    "new_game", "legal_actions", "apply_action", "longest_road_length",
]

"""Shared test helpers for building legal in-play positions against the engine.

Kept in one place so the road-connectivity setup isn't duplicated across test
modules (the engine requires settlements to connect to the player's roads
during normal play, so exercising an in-play placement needs a real road path).
"""
from app.models.board import HexCoord
from app.services.game_service import GameService


def place_free_setup_settlement(game, player_id=0):
    """Place one free setup settlement at a central vertex; returns the vertex."""
    for v in game.board.get_vertices_for_hex(HexCoord(0, 0)):
        ok, _ = GameService.place_settlement(game, player_id, v)
        if ok:
            return v
    raise AssertionError("no legal setup vertex found")


def extend_two_roads(game, player_id):
    """Find a 2-road path from the player's first settlement to a legal in-play
    settlement vertex (2 edges away, so the distance rule allows building there).
    Returns (edge1, edge2, target_vertex)."""
    board = game.board
    start = game.players[player_id].settlements[0].vertex
    all_edges, all_vertices = board.get_all_edges(), board.get_all_vertices()
    for e1 in board.get_edges_for_vertex(start):
        if e1 not in all_edges:
            continue
        mids = [w for w in board.get_edge_endpoints(e1) if w != start]
        if not mids:
            continue
        mid = mids[0]
        for e2 in board.get_edges_for_vertex(mid):
            if e2 == e1 or e2 not in all_edges:
                continue
            for target in board.get_edge_endpoints(e2):
                if target in (mid, start) or target not in all_vertices:
                    continue
                if any(s.vertex == target for s in game.settlements_on_board):
                    continue
                if any(GameService._vertices_are_adjacent(board, target, s.vertex)
                       for s in game.settlements_on_board):
                    continue
                return e1, e2, target
    raise AssertionError("no 2-road path to a legal vertex found")

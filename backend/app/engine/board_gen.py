"""Random board generation per CATAN_1V1_RULES.md §1–§2.

- Terrain: 4 forest / 4 pasture / 4 fields / 3 hills / 3 mountains / 1 desert.
- Tokens: the 18-value set (no 7); desert gets none; robber starts there.
- D5: the four red-number hexes (6s and 8s) are never adjacent.
- D6 (simplified ports): 9 ports — 4 generic 3:1 + one 2:1 per resource —
  assigned to evenly spaced coastal vertices (exact coastal geometry deferred).
"""
import math
import random
from typing import Dict, List, Optional, Tuple

from app.models.board import Board, HexCoord, Resource, STANDARD_COORDS, Vertex

TERRAIN_POOL: List[Optional[Resource]] = (
    [Resource.WOOD] * 4 + [Resource.SHEEP] * 4 + [Resource.WHEAT] * 4
    + [Resource.BRICK] * 3 + [Resource.ORE] * 3 + [None]  # None = desert
)
NUMBER_TOKENS = [2, 3, 3, 4, 4, 5, 5, 6, 6, 8, 8, 9, 9, 10, 10, 11, 11, 12]
PORT_POOL: List[Optional[Resource]] = (
    [None] * 4  # generic 3:1
    + [Resource.WOOD, Resource.BRICK, Resource.SHEEP, Resource.WHEAT, Resource.ORE]  # 2:1
)

Layout = List[Tuple[HexCoord, Optional[Resource], Optional[int]]]


def _red_numbers_ok(layout: Layout) -> bool:
    """D5: no two of the 6/8 hexes may touch."""
    red = [c for c, _, n in layout if n in (6, 8)]
    red_set = set(red)
    return all(nb not in red_set for c in red for nb in c.neighbors())


def generate_board(rng: random.Random) -> Tuple[Board, HexCoord, Dict[Vertex, Optional[Resource]]]:
    """Build a random board. Returns (board, desert_coord, ports)."""
    terrain = TERRAIN_POOL[:]
    rng.shuffle(terrain)
    for _ in range(10_000):  # red-number rule is easy to satisfy; retry tokens
        tokens = NUMBER_TOKENS[:]
        rng.shuffle(tokens)
        it = iter(tokens)
        layout: Layout = [
            (coord, res, None if res is None else next(it))
            for coord, res in zip(STANDARD_COORDS, terrain)
        ]
        if _red_numbers_ok(layout):
            break
    else:  # pragma: no cover — statistically unreachable
        raise RuntimeError("board generation could not satisfy the red-number rule")

    board = Board(layout=layout)
    desert = next(c for c, res, _ in layout if res is None)
    return board, desert, _assign_ports(board, rng)


def _vertex_position(v: Vertex) -> Tuple[float, float]:
    """Cartesian centroid of a vertex's three hex coords (for coastal ordering)."""
    xs = [c.q + c.r / 2 for c in v.hex_coords]
    ys = [c.r * math.sqrt(3) / 2 for c in v.hex_coords]
    return sum(xs) / 3, sum(ys) / 3


def coastal_vertices(board: Board) -> List[Vertex]:
    """Vertices on the coastline (fewer than 3 of their hexes are on the board),
    ordered by angle around the board center — deterministic given the board."""
    coast = [
        v for v in board.get_all_vertices()
        if sum(1 for c in v.hex_coords if board.hex_exists(c)) < 3
    ]

    def key(v: Vertex):
        x, y = _vertex_position(v)
        return (math.atan2(y, x), x * x + y * y, sorted((c.q, c.r) for c in v.hex_coords))

    return sorted(coast, key=key)


def _assign_ports(board: Board, rng: random.Random) -> Dict[Vertex, Optional[Resource]]:
    """D6 simplified: shuffle the 9 port types onto evenly spaced coastal vertices."""
    coast = coastal_vertices(board)
    types = PORT_POOL[:]
    rng.shuffle(types)
    step = len(coast) // len(types)
    return {coast[i * step]: t for i, t in enumerate(types)}

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Set, Tuple, Optional


class Resource(str, Enum):
    WOOD = "wood"
    WHEAT = "wheat"
    ORE = "ore"
    BRICK = "brick"
    SHEEP = "sheep"


@dataclass
class HexCoord:
    """Axial hex coordinate (q, r). Converts to/from cube coordinates for math."""
    q: int
    r: int

    def __hash__(self):
        return hash((self.q, self.r))

    def __eq__(self, other):
        if isinstance(other, HexCoord):
            return self.q == other.q and self.r == other.r
        return False

    def to_cube(self) -> Tuple[int, int, int]:
        """Convert axial (q, r) to cube (x, y, z) where x + y + z = 0."""
        x = self.q
        z = self.r
        y = -x - z
        return (x, y, z)

    @staticmethod
    def from_cube(x: int, y: int, z: int) -> "HexCoord":
        """Convert cube (x, y, z) to axial (q, r)."""
        return HexCoord(x, z)

    def neighbors(self) -> List["HexCoord"]:
        """Return the 6 neighboring hex coordinates."""
        directions = [
            (1, 0), (1, -1), (0, -1),
            (-1, 0), (-1, 1), (0, 1)
        ]
        return [HexCoord(self.q + dq, self.r + dr) for dq, dr in directions]


@dataclass
class Vertex:
    """A vertex is a corner shared by up to 3 hexes. Identified by 3 adjacent hex coords."""
    hex_coords: Tuple[HexCoord, HexCoord, HexCoord]

    def __hash__(self):
        return hash(tuple(sorted([(h.q, h.r) for h in self.hex_coords])))

    def __eq__(self, other):
        if isinstance(other, Vertex):
            return set(self.hex_coords) == set(other.hex_coords)
        return False


@dataclass
class Edge:
    """An edge connects two vertices. Identified by 2 hex coordinates."""
    hex1: HexCoord
    hex2: HexCoord

    def __hash__(self):
        # Normalize so edges are the same regardless of order
        h1 = (self.hex1.q, self.hex1.r)
        h2 = (self.hex2.q, self.hex2.r)
        return hash(tuple(sorted([h1, h2])))

    def __eq__(self, other):
        if isinstance(other, Edge):
            h1_set = {(self.hex1.q, self.hex1.r), (self.hex2.q, self.hex2.r)}
            h2_set = {(other.hex1.q, other.hex1.r), (other.hex2.q, other.hex2.r)}
            return h1_set == h2_set
        return False


@dataclass
class Hex:
    """A single hexagon on the board."""
    coord: HexCoord
    resource: Optional[Resource]
    dice_number: Optional[int]  # 2-12, None if desert

    def __hash__(self):
        return hash(self.coord)

    def __eq__(self, other):
        if isinstance(other, Hex):
            return self.coord == other.coord
        return False


class Board:
    """Hexagonal board with 19 hexes (standard Catan layout)."""

    def __init__(self):
        """Initialize board with 19 hexes in standard Catan pattern."""
        self.hexes: Dict[HexCoord, Hex] = {}
        self._init_hexes()

    def _init_hexes(self):
        """Create 19 hexes in standard Catan layout using axial coordinates.
        Layout (numbers are ring distance):
              0   1   2
            3   4   5   6
          7   8   9  10  11
            12  13  14  15
              16  17  18
        """
        coords = [
            # Center
            HexCoord(0, 0),
            # Ring 1 (6 hexes)
            HexCoord(1, 0), HexCoord(1, -1), HexCoord(0, -1),
            HexCoord(-1, 0), HexCoord(-1, 1), HexCoord(0, 1),
            # Ring 2 (12 hexes)
            HexCoord(2, 0), HexCoord(2, -1), HexCoord(2, -2),
            HexCoord(1, -2), HexCoord(0, -2), HexCoord(-1, -1),
            HexCoord(-2, 0), HexCoord(-2, 1), HexCoord(-2, 2),
            HexCoord(-1, 2), HexCoord(0, 2), HexCoord(1, 1),
        ]
        resources = [
            Resource.WHEAT,  # 0
            Resource.SHEEP, Resource.ORE, Resource.BRICK,  # 1-3
            Resource.WOOD, Resource.WHEAT, Resource.BRICK,  # 4-6
            Resource.ORE, Resource.SHEEP, Resource.WOOD,  # 7-9
            Resource.BRICK, Resource.WHEAT, Resource.SHEEP,  # 10-12
            Resource.WOOD, Resource.ORE, Resource.WOOD,  # 13-15
            Resource.SHEEP, Resource.BRICK, Resource.WHEAT,  # 16-18
        ]
        dice_numbers = [
            6,  # 0
            5, 10, 8,  # 1-3
            9, 4, 11,  # 4-6
            3, 11, 4,  # 7-9
            8, 10, 5,  # 10-12
            6, 9, 2,  # 13-15
            3, 12, 7,  # 16-18
        ]
        for coord, resource, dice_num in zip(coords, resources, dice_numbers):
            self.hexes[coord] = Hex(coord, resource, dice_num)

    def get_hex(self, coord: HexCoord) -> Optional[Hex]:
        """Get hex at coordinate."""
        return self.hexes.get(coord)

    def hex_exists(self, coord: HexCoord) -> bool:
        """Check if hex exists on board."""
        return coord in self.hexes

    def get_hexes_by_dice_number(self, dice_number: int) -> List[Hex]:
        """Get all hexes matching a dice roll number."""
        return [h for h in self.hexes.values() if h.dice_number == dice_number]

    def get_adjacent_hexes(self, coord: HexCoord) -> List[Hex]:
        """Get all hexes adjacent to a coordinate that exist on the board."""
        hexes = []
        for neighbor_coord in coord.neighbors():
            if hex := self.get_hex(neighbor_coord):
                hexes.append(hex)
        return hexes

    def get_vertices_for_hex(self, coord: HexCoord) -> List[Vertex]:
        """Get all 6 vertices (corners) of a hex.
        Each vertex is shared by up to 3 hexes."""
        neighbors = coord.neighbors()
        vertices = []
        # Each hex has 6 vertices defined by combinations of itself and neighbors
        for i in range(6):
            neighbor1 = neighbors[i]
            neighbor2 = neighbors[(i + 1) % 6]
            vertex = Vertex((coord, neighbor1, neighbor2))
            vertices.append(vertex)
        return vertices

    def get_edges_for_hex(self, coord: HexCoord) -> List[Edge]:
        """Get all 6 edges of a hex."""
        neighbors = coord.neighbors()
        edges = []
        for i in range(6):
            edge = Edge(coord, neighbors[i])
            edges.append(edge)
        return edges

    def get_edges_for_vertex(self, vertex: Vertex) -> List[Edge]:
        """Get the 3 edges incident to a vertex.

        A vertex is the corner shared by 3 hexes (a, b, c). The edges meeting
        at that corner are the borders between each pair of those hexes.
        """
        a, b, c = vertex.hex_coords
        return [Edge(a, b), Edge(b, c), Edge(a, c)]

    def get_edge_endpoints(self, edge: Edge) -> List[Vertex]:
        """Get the 2 vertices at the ends of an edge.

        An edge borders hexes h1 and h2. The two adjacent hexes that h1 and h2
        share (their common neighbors) define the two endpoint corners.
        """
        common = [n for n in edge.hex1.neighbors() if n in set(edge.hex2.neighbors())]
        return [Vertex((edge.hex1, edge.hex2, c)) for c in common]

    def get_hexes_for_vertex(self, vertex: Vertex) -> List[Hex]:
        """Get up to 3 hexes that share a vertex."""
        hexes = []
        for coord in vertex.hex_coords:
            if hex := self.get_hex(coord):
                hexes.append(hex)
        return hexes

    def get_hexes_for_edge(self, edge: Edge) -> List[Hex]:
        """Get the 2 hexes that share an edge."""
        hexes = []
        if hex1 := self.get_hex(edge.hex1):
            hexes.append(hex1)
        if hex2 := self.get_hex(edge.hex2):
            hexes.append(hex2)
        return hexes

    def get_neighboring_vertices(self, vertex: Vertex) -> List[Vertex]:
        """Get the 3 vertices adjacent to a given vertex."""
        # A vertex touches 3 hexes. Its neighbors are the other vertices
        # on those hexes that share an edge with this vertex.
        adjacent_vertices = set()
        for hex_coord in vertex.hex_coords:
            if hex := self.get_hex(hex_coord):
                for v in self.get_vertices_for_hex(hex_coord):
                    # Two vertices are neighbors if they share 2 hexes
                    if len(set(v.hex_coords) & set(vertex.hex_coords)) == 2:
                        adjacent_vertices.add(v)
        return list(adjacent_vertices)

    def get_all_vertices(self) -> Set[Vertex]:
        """Get all valid vertices on the board."""
        vertices = set()
        for hex_coord in self.hexes:
            for vertex in self.get_vertices_for_hex(hex_coord):
                vertices.add(vertex)
        return vertices

    def get_all_edges(self) -> Set[Edge]:
        """Get all valid edges on the board."""
        edges = set()
        for hex_coord in self.hexes:
            for edge in self.get_edges_for_hex(hex_coord):
                edges.add(edge)
        return edges

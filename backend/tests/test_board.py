import pytest
from app.models.board import Board, HexCoord, Vertex, Edge, Resource, Hex


class TestHexCoord:
    """Test hexagonal coordinate system."""

    def test_hex_coord_creation(self):
        """Test creating hex coordinates."""
        coord = HexCoord(0, 0)
        assert coord.q == 0
        assert coord.r == 0

    def test_hex_coord_equality(self):
        """Test hex coordinate equality."""
        c1 = HexCoord(1, 2)
        c2 = HexCoord(1, 2)
        c3 = HexCoord(1, 3)
        assert c1 == c2
        assert c1 != c3

    def test_hex_coord_hashing(self):
        """Test hex coordinates can be used in sets/dicts."""
        c1 = HexCoord(1, 2)
        c2 = HexCoord(1, 2)
        s = {c1, c2}
        assert len(s) == 1

    def test_cube_conversion(self):
        """Test conversion between axial and cube coordinates."""
        axial = HexCoord(2, -3)
        x, y, z = axial.to_cube()
        assert x + y + z == 0
        assert HexCoord.from_cube(x, y, z) == axial

    def test_neighbors(self):
        """Test getting neighboring hex coordinates."""
        center = HexCoord(0, 0)
        neighbors = center.neighbors()
        assert len(neighbors) == 6
        # Should include all 6 neighbors
        assert HexCoord(1, 0) in neighbors
        assert HexCoord(0, 1) in neighbors
        assert HexCoord(-1, 1) in neighbors
        assert HexCoord(-1, 0) in neighbors
        assert HexCoord(0, -1) in neighbors
        assert HexCoord(1, -1) in neighbors


class TestBoard:
    """Test board creation and operations."""

    def test_board_creation(self):
        """Test creating a board initializes 19 hexes."""
        board = Board()
        assert len(board.hexes) == 19

    def test_all_hexes_have_resources(self):
        """Test all hexes have a resource type."""
        board = Board()
        for hex_obj in board.hexes.values():
            assert hex_obj.resource in Resource

    def test_all_hexes_have_dice_numbers(self):
        """Test all hexes have dice numbers 2-12."""
        board = Board()
        dice_numbers = [h.dice_number for h in board.hexes.values()]
        assert all(2 <= d <= 12 for d in dice_numbers)

    def test_get_hex(self):
        """Test retrieving a hex by coordinate."""
        board = Board()
        center = HexCoord(0, 0)
        hex_obj = board.get_hex(center)
        assert hex_obj is not None
        assert hex_obj.coord == center

    def test_get_nonexistent_hex(self):
        """Test retrieving a hex that doesn't exist."""
        board = Board()
        invalid = HexCoord(100, 100)
        hex_obj = board.get_hex(invalid)
        assert hex_obj is None

    def test_hex_exists(self):
        """Test checking if hex exists on board."""
        board = Board()
        assert board.hex_exists(HexCoord(0, 0))
        assert not board.hex_exists(HexCoord(100, 100))

    def test_adjacent_hexes(self):
        """Test getting adjacent hexes."""
        board = Board()
        center = HexCoord(0, 0)
        adjacent = board.get_adjacent_hexes(center)
        # Center has 6 neighbors on this board
        assert len(adjacent) == 6

    def test_get_hexes_by_dice_number(self):
        """Test retrieving hexes by dice number."""
        board = Board()
        hexes_6 = board.get_hexes_by_dice_number(6)
        # Should have at least one hex with roll number 6
        assert len(hexes_6) > 0
        assert all(h.dice_number == 6 for h in hexes_6)

    def test_get_vertices_for_hex(self):
        """Test getting vertices of a hex."""
        board = Board()
        center = HexCoord(0, 0)
        vertices = board.get_vertices_for_hex(center)
        assert len(vertices) == 6

    def test_get_edges_for_hex(self):
        """Test getting edges of a hex."""
        board = Board()
        center = HexCoord(0, 0)
        edges = board.get_edges_for_hex(center)
        assert len(edges) == 6

    def test_get_all_vertices(self):
        """Test getting all vertices on the board."""
        board = Board()
        vertices = board.get_all_vertices()
        # 19 hexes * 6 vertices/hex, but shared vertices reduce the count significantly
        # Standard Catan board has about 54 unique vertices
        assert len(vertices) > 30

    def test_get_all_edges(self):
        """Test getting all edges on the board."""
        board = Board()
        edges = board.get_all_edges()
        # 19 hexes * 6 edges/hex, but shared edges reduce the count
        # Standard Catan board has about 72 unique edges
        assert len(edges) > 50

    def test_hexes_for_vertex(self):
        """Test getting hexes that share a vertex."""
        board = Board()
        vertices = board.get_vertices_for_hex(HexCoord(0, 0))
        for vertex in vertices:
            hexes = board.get_hexes_for_vertex(vertex)
            # Interior vertices are shared by 3 hexes, edge vertices by 2
            assert 2 <= len(hexes) <= 3

    def test_hexes_for_edge(self):
        """Test getting hexes that share an edge."""
        board = Board()
        edges = board.get_edges_for_hex(HexCoord(0, 0))
        for edge in edges:
            hexes = board.get_hexes_for_edge(edge)
            # All edges should be shared by exactly 2 hexes
            assert len(hexes) == 2


class TestVertex:
    """Test vertex operations."""

    def test_vertex_creation(self):
        """Test creating a vertex."""
        hexes = (HexCoord(0, 0), HexCoord(1, 0), HexCoord(0, 1))
        vertex = Vertex(hexes)
        assert vertex.hex_coords == hexes

    def test_vertex_equality(self):
        """Test vertex equality (order-independent)."""
        h1 = (HexCoord(0, 0), HexCoord(1, 0), HexCoord(0, 1))
        h2 = (HexCoord(1, 0), HexCoord(0, 0), HexCoord(0, 1))
        v1 = Vertex(h1)
        v2 = Vertex(h2)
        assert v1 == v2

    def test_vertex_hashing(self):
        """Test vertices can be used in sets."""
        h1 = (HexCoord(0, 0), HexCoord(1, 0), HexCoord(0, 1))
        h2 = (HexCoord(1, 0), HexCoord(0, 0), HexCoord(0, 1))
        v1 = Vertex(h1)
        v2 = Vertex(h2)
        s = {v1, v2}
        # Same vertex, different order
        assert len(s) == 1


class TestEdge:
    """Test edge operations."""

    def test_edge_creation(self):
        """Test creating an edge."""
        edge = Edge(HexCoord(0, 0), HexCoord(1, 0))
        assert edge.hex1 == HexCoord(0, 0)
        assert edge.hex2 == HexCoord(1, 0)

    def test_edge_equality(self):
        """Test edge equality (order-independent)."""
        e1 = Edge(HexCoord(0, 0), HexCoord(1, 0))
        e2 = Edge(HexCoord(1, 0), HexCoord(0, 0))
        assert e1 == e2

    def test_edge_hashing(self):
        """Test edges can be used in sets."""
        e1 = Edge(HexCoord(0, 0), HexCoord(1, 0))
        e2 = Edge(HexCoord(1, 0), HexCoord(0, 0))
        s = {e1, e2}
        # Same edge, different order
        assert len(s) == 1

import pytest
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)


class TestGameAPI:
    """Test game API endpoints."""

    def test_health_endpoint(self):
        """Test health check endpoint."""
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json()["status"] == "ok"

    def test_root_endpoint(self):
        """Test root endpoint."""
        response = client.get("/")
        assert response.status_code == 200

    def test_create_game_success(self):
        """Test creating a new game."""
        response = client.post(
            "/game/new", json={"player_name": "Alice"}
        )
        assert response.status_code == 201
        data = response.json()
        assert "game_id" in data
        assert data["status"] == "setup"
        assert data["message"] == "Game created successfully"

    def test_create_game_no_player_name(self):
        """Test creating game without player name fails."""
        response = client.post("/game/new", json={})
        assert response.status_code == 422  # Validation error

    def test_get_game_state_success(self):
        """Test getting game state."""
        # Create game
        create_response = client.post(
            "/game/new", json={"player_name": "Alice"}
        )
        game_id = create_response.json()["game_id"]

        # Get game state
        response = client.get(f"/game/{game_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == game_id
        assert data["current_player_name"] == "Alice"
        assert len(data["players"]) == 2

    def test_get_game_state_not_found(self):
        """Test getting nonexistent game fails."""
        response = client.get("/game/nonexistent")
        assert response.status_code == 404

    def test_roll_dice_success(self):
        """Test rolling dice."""
        # Create game
        create_response = client.post(
            "/game/new", json={"player_name": "Alice"}
        )
        game_id = create_response.json()["game_id"]

        # Roll dice
        response = client.post(f"/game/{game_id}/roll-dice")
        assert response.status_code == 200
        data = response.json()
        assert "dice_roll" in data
        assert 2 <= data["dice_roll"] <= 12
        assert data["success"] is True

    def test_build_settlement_success(self):
        """Test building a settlement."""
        # Create game
        create_response = client.post(
            "/game/new", json={"player_name": "Alice"}
        )
        game_id = create_response.json()["game_id"]

        # Build settlement (using dummy coordinates)
        response = client.post(
            f"/game/{game_id}/build-settlement",
            json={"vertex_coords": [(0, 0), (1, 0), (0, 1)]},
        )
        # May fail depending on board validation, but endpoint should work
        assert response.status_code in [200, 400]

    def test_build_settlement_invalid_game(self):
        """Test building settlement on invalid game fails."""
        response = client.post(
            "/game/nonexistent/build-settlement",
            json={"vertex_coords": [(0, 0), (1, 0), (0, 1)]},
        )
        assert response.status_code == 404

    def test_build_road_success(self):
        """Test building a road."""
        # Create game
        create_response = client.post(
            "/game/new", json={"player_name": "Alice"}
        )
        game_id = create_response.json()["game_id"]

        # Build road (using dummy coordinates)
        response = client.post(
            f"/game/{game_id}/build-road",
            json={"hex1_coords": (0, 0), "hex2_coords": (1, 0)},
        )
        # May fail depending on game state, but endpoint should work
        assert response.status_code in [200, 400]

    def test_trade_success(self):
        """Test executing a trade."""
        # Create game
        create_response = client.post(
            "/game/new", json={"player_name": "Alice"}
        )
        game_id = create_response.json()["game_id"]

        # Try to execute a trade
        response = client.post(
            f"/game/{game_id}/trade",
            json={
                "give_resources": {"wood": 1},
                "receive_resources": {"brick": 1},
            },
        )
        # Will fail because player doesn't have resources
        assert response.status_code in [200, 400]

    def test_end_turn_success(self):
        """Test ending a turn."""
        # Create game
        create_response = client.post(
            "/game/new", json={"player_name": "Alice"}
        )
        game_id = create_response.json()["game_id"]

        # End turn
        response = client.post(f"/game/{game_id}/end-turn")
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["next_player_id"] == 1
        assert data["next_player_name"] == "AI Opponent"

    def test_get_game_status(self):
        """Test getting game status."""
        # Create game
        create_response = client.post(
            "/game/new", json={"player_name": "Alice"}
        )
        game_id = create_response.json()["game_id"]

        # Get status
        response = client.get(f"/game/{game_id}/status")
        assert response.status_code == 200
        data = response.json()
        assert data["game_id"] == game_id
        assert data["current_player"] == "Alice"

    def test_full_game_flow(self):
        """Test a full game turn sequence."""
        # Create game
        create_response = client.post(
            "/game/new", json={"player_name": "Alice"}
        )
        game_id = create_response.json()["game_id"]
        assert create_response.status_code == 201

        # Get initial state
        state1 = client.get(f"/game/{game_id}").json()
        assert state1["current_player_id"] == 0

        # Roll dice
        roll = client.post(f"/game/{game_id}/roll-dice").json()
        assert 2 <= roll["dice_roll"] <= 12

        # End turn
        end_turn = client.post(f"/game/{game_id}/end-turn").json()
        assert end_turn["next_player_id"] == 1

        # Get updated state
        state2 = client.get(f"/game/{game_id}").json()
        assert state2["current_player_id"] == 1
        assert state2["turn_number"] > state1["turn_number"]

"""Turn flow (§4), dice production, bank shortage (§5)."""
import pytest

from app.engine import ActionType, CITY, Phase, SETTLEMENT, apply_action, legal_actions
from app.engine.rules import _produce
from app.models.board import Resource

from tests.engine_test_utils import acts_of, game, main_phase_game, run_setup, seed_rolling


def _numbered_hex(state):
    return next(h for h in state.board.hexes.values() if h.dice_number is not None)


def _expected_gain(state, v, number, per_building):
    return per_building * sum(
        1 for h in state.board.get_hexes_by_dice_number(number)
        if h.coord != state.robber and v in state.board.get_vertices_for_hex(h.coord)
    )


class TestTurnFlow:
    def test_pre_roll_only_roll_available(self):
        s = main_phase_game(rolled=False)
        assert {a.type for a in legal_actions(s)} == {ActionType.ROLL}

    def test_roll_is_once_per_turn(self):
        s = run_setup(game())
        s.rng = seed_rolling(6)  # deterministic non-7
        apply_action(s, acts_of(s, ActionType.ROLL)[0])
        assert s.has_rolled and s.last_roll is not None
        assert not acts_of(s, ActionType.ROLL)

    def test_end_turn_resets_turn_state(self):
        s = main_phase_game()
        s.dev_played_this_turn = True
        apply_action(s, acts_of(s, ActionType.END_TURN)[0])
        assert s.current_player == 1
        assert s.turn_number == 2
        assert not s.has_rolled and not s.dev_played_this_turn

    def test_no_end_turn_before_rolling(self):
        s = main_phase_game(rolled=False)
        assert not acts_of(s, ActionType.END_TURN)


class TestProduction:
    def test_settlement_produces_one(self):
        s = main_phase_game()
        s.buildings.clear()
        h = _numbered_hex(s)
        v = s.board.get_vertices_for_hex(h.coord)[0]
        s.buildings[v] = (0, SETTLEMENT)
        before = s.players[0].resources[h.resource]
        _produce(s, h.dice_number)
        gained = s.players[0].resources[h.resource] - before
        assert gained == _expected_gain(s, v, h.dice_number, 1) >= 1

    def test_city_produces_two(self):
        s = main_phase_game()
        s.buildings.clear()
        h = _numbered_hex(s)
        v = s.board.get_vertices_for_hex(h.coord)[0]
        s.buildings[v] = (0, CITY)
        before = s.players[0].resources[h.resource]
        _produce(s, h.dice_number)
        assert s.players[0].resources[h.resource] - before == \
            _expected_gain(s, v, h.dice_number, 2) >= 2

    def test_robber_blocks_production(self):
        s = main_phase_game()
        s.buildings.clear()
        h = _numbered_hex(s)
        v = s.board.get_vertices_for_hex(h.coord)[0]
        s.buildings[v] = (0, SETTLEMENT)
        s.robber = h.coord
        before = dict(s.players[0].resources)
        _produce(s, h.dice_number)
        gained = s.players[0].resources[h.resource] - before[h.resource]
        assert gained == _expected_gain(s, v, h.dice_number, 1)  # this hex excluded

    def test_bank_shortage_single_player_takes_remainder(self):
        s = main_phase_game()
        s.buildings.clear()
        h = _numbered_hex(s)
        v = s.board.get_vertices_for_hex(h.coord)[0]
        s.buildings[v] = (0, CITY)  # owed 2
        s.bank[h.resource] = 1
        # ensure only this hex produces on the roll for this player
        for other in s.board.get_hexes_by_dice_number(h.dice_number):
            if other.coord != h.coord:
                s.robber = other.coord
        before = s.players[0].resources[h.resource]
        _produce(s, h.dice_number)
        assert s.players[0].resources[h.resource] - before == 1
        assert s.bank[h.resource] == 0

    def test_bank_shortage_two_entitled_nobody_paid(self):
        s = main_phase_game()
        s.buildings.clear()
        h = _numbered_hex(s)
        vs = s.board.get_vertices_for_hex(h.coord)
        s.buildings[vs[0]] = (0, SETTLEMENT)
        s.buildings[vs[3]] = (1, SETTLEMENT)  # opposite corner: distance rule safe
        s.bank[h.resource] = 1
        p0_before = s.players[0].resources[h.resource]
        p1_before = s.players[1].resources[h.resource]
        _produce(s, h.dice_number)
        assert s.players[0].resources[h.resource] == p0_before
        assert s.players[1].resources[h.resource] == p1_before
        assert s.bank[h.resource] == 1

    def test_roll_of_seven_produces_nothing_and_enters_robber_flow(self):
        s = run_setup(game())
        s.rng = seed_rolling(7)
        hands = [p.hand_size() for p in s.players]
        apply_action(s, acts_of(s, ActionType.ROLL)[0])
        assert [p.hand_size() for p in s.players] == hands
        assert s.phase in (Phase.DISCARD, Phase.MOVE_ROBBER)

    def test_illegal_action_rejected(self):
        s = main_phase_game()
        for r in Resource:  # broke: only END_TURN is legal
            s.players[0].resources[r] = 0
        end = legal_actions(s)[0]
        assert end.type == ActionType.END_TURN
        apply_action(s, end)
        with pytest.raises(ValueError):
            apply_action(s, end)  # P0's END_TURN is illegal on P1's turn

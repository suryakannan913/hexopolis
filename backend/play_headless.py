"""
Headless Hexopolis — play the game purely through the logic layer.

No UI, no web server, no HTTP: this imports the game logic directly and
renders the board + state as text. It's a probe to demonstrate that the
rules engine can run on its own.

Run from the backend/ directory:
    python3 play_headless.py
"""
from app.models.board import HexCoord, Vertex, Resource
from app.models.game import Game, GameStatus
from app.services.game_service import GameService


# ---------- text rendering ----------

RES_SHORT = {
    Resource.WOOD: "wood",
    Resource.WHEAT: "wheat",
    Resource.ORE: "ore",
    Resource.BRICK: "brick",
    Resource.SHEEP: "sheep",
}
CELL = 9
ROW_ORDER = [-2, -1, 0, 1, 2]  # board rows, top to bottom (axial r)


def _cell(text):
    return text.center(CELL)


def render_board(game) -> str:
    """Render the 19-hex board as staggered text rows (3-4-5-4-3)."""
    hexes = list(game.board.hexes.values())
    rows = {}
    for h in hexes:
        rows.setdefault(h.coord.r, []).append(h)
    for r in rows:
        rows[r].sort(key=lambda h: h.coord.q + h.coord.r / 2)  # left-to-right

    width = max(len(v) for v in rows.values())
    lines = []
    for r in ROW_ORDER:
        row = rows.get(r, [])
        indent = " " * ((width - len(row)) * CELL // 2)
        res_line, num_line = [], []
        for h in row:
            if h.dice_number == 7 or h.resource is None:
                res_line.append(_cell("desert"))
                num_line.append(_cell("( 7R )"))
            else:
                res_line.append(_cell(RES_SHORT[h.resource]))
                n = h.dice_number
                tok = f"{n}*" if n in (6, 8) else str(n)  # * = high odds
                num_line.append(_cell(f"({tok})"))
        lines.append(indent + "".join(res_line))
        lines.append(indent + "".join(num_line))
        lines.append("")
    return "\n".join(lines)


def _vkey(vertex: Vertex) -> str:
    cs = sorted((h.q, h.r) for h in vertex.hex_coords)
    return "/".join(f"({q},{r})" for q, r in cs)


def render_state(game) -> str:
    out = []
    status = game.status.value
    cur = game.get_current_player()
    out.append(f"status={status}  turn={game.turn_number}  "
               f"current={cur.name}  last_roll={game.last_dice_roll}")
    for p in game.players:
        res = " ".join(f"{RES_SHORT[r][:2]}:{p.resources[r]}" for r in Resource)
        out.append(f"  [{p.player_type.value:5}] {p.name:12} pts={p.points}  "
                   f"settlements={len(p.settlements)} roads={len(p.roads)}  | {res}")
    if game.settlements_on_board:
        out.append("  Settlements:")
        for s in game.settlements_on_board:
            out.append(f"    P{s.owner_id} @ {_vkey(s.vertex)}")
    if game.roads_on_board:
        out.append("  Roads:")
        for rd in game.roads_on_board:
            e = rd.edge
            out.append(f"    P{rd.owner_id} @ ({e.hex1.q},{e.hex1.r})-({e.hex2.q},{e.hex2.r})")
    return "\n".join(out)


def banner(title):
    print("\n" + "=" * 64)
    print(title)
    print("=" * 64)


# ---------- driving the game through the logic layer ----------

def first_legal_setup_vertex(game, player_id):
    """Pick a legal opening-settlement vertex (no UI, just the rules)."""
    best, best_score = None, -1
    for v in game.board.get_all_vertices():
        if any(s.vertex == v for s in game.settlements_on_board):
            continue
        if any(GameService._vertices_are_adjacent(game.board, v, s.vertex)
               for s in game.settlements_on_board):
            continue
        # prefer vertices touching more producing hexes
        score = sum(1 for h in game.board.get_hexes_for_vertex(v) if h.resource)
        if score > best_score:
            best, best_score = v, score
    return best


def try_build_something(game, player_id):
    """Attempt one road then one settlement for the human, if legal/affordable."""
    player = game.players[player_id]
    log = []
    # road off an existing settlement
    for s in player.settlements:
        for edge in game.board.get_edges_for_vertex(s.vertex):
            ok, err = GameService.build_road(game, player_id, edge)
            if ok:
                log.append(f"built road @ ({edge.hex1.q},{edge.hex1.r})-({edge.hex2.q},{edge.hex2.r})")
                break
        if log:
            break
    return log


def main():
    banner("NEW GAME (created via GameService — no UI involved)")
    game = GameService.create_game("headless-1", "ScriptPlayer")
    print(render_board(game))
    print(render_state(game))

    # --- opening placement: human places 2, engine auto-places AI ---
    banner("OPENING PLACEMENT")
    for i in range(GameService.INITIAL_SETTLEMENTS_PER_PLAYER):
        v = first_legal_setup_vertex(game, 0)
        ok, err = GameService.place_settlement(game, 0, v)
        print(f"  human places settlement {i+1} -> {'OK' if ok else 'FAIL: ' + err} @ {_vkey(v)}")
    print()
    print(render_board(game))
    print(render_state(game))

    # --- play turns until someone wins or we hit a turn cap ---
    banner("PLAYING TURNS")
    TURN_CAP = 30
    while game.status != GameStatus.WON and game.turn_number <= TURN_CAP:
        cur = game.get_current_player()
        if cur.player_type.value == "human":
            roll = GameService.roll_dice(game)
            GameService.distribute_resources(game, roll)
            line = f"Turn {game.turn_number}: {cur.name} rolled {roll}"
            builds = try_build_something(game, 0)
            if builds:
                line += " | " + "; ".join(builds)
            print(line)
            GameService.end_turn(game)
        else:
            GameService.execute_ai_turn(game, cur.id)
            print(f"Turn {game.turn_number - 1}: {cur.name} took its turn "
                  f"(pts={cur.points}, settlements={len(cur.settlements)}, roads={len(cur.roads)})")

    banner("FINAL STATE")
    print(render_board(game))
    print(render_state(game))
    if game.status == GameStatus.WON:
        winner = max(game.players, key=lambda p: p.points)
        print(f"\n>>> {winner.name} wins with {winner.points} points!")
    else:
        print(f"\n>>> Reached turn cap ({TURN_CAP}); no winner yet "
              f"(win target is {GameService.WINNING_POINTS} points).")


if __name__ == "__main__":
    main()

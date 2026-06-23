"""Headless logic checks for the Gomoku core (no terminal required).

Run with ``python selftest.py``. Exercises win detection in all four
orientations at exactly five, the absence of a false win at four, the place
transition (occupied-cell rejection, draw on a full board), immutability, the
threat-pattern AI (legal moves, taking an immediate win, blocking the opponent's
open four / immediate win, deterministic tie-break with a seeded RNG), and
render string composition, so the game can be verified in CI or over SSH without
a TTY.
"""
from __future__ import annotations

import io
import random
from contextlib import redirect_stdout

import board as B
import game as G


def check(condition: bool, label: str) -> None:
    if not condition:
        raise AssertionError(f"FAILED: {label}")
    print(f"ok - {label}")


def _empty_board() -> G.Board:
    """A fresh 15x15 board of zeros."""
    return tuple(tuple(0 for _ in range(B.COLS)) for _ in range(B.ROWS))


def _with(board: G.Board, cells: list[tuple[int, int, int]]) -> G.Board:
    """Return *board* with each (row, col, value) applied."""
    grid = [list(row) for row in board]
    for r, c, v in cells:
        grid[r][c] = v
    return tuple(tuple(row) for row in grid)


def _run(start_r: int, start_c: int, dr: int, dc: int, n: int, value: int):
    """Return cell tuples for an n-length run of *value* from a start cell."""
    return [(start_r + dr * k, start_c + dc * k, value) for k in range(n)]


def _state(board: G.Board, player: int = G.HUMAN, cursor=(0, 0)) -> G.GameState:
    """Wrap a board in a fresh, in-progress GameState."""
    return G.GameState(
        board=board,
        current_player=player,
        game_over=False,
        winner=None,
        last_move=None,
        cursor=cursor,
    )


# ---------------------------------------------------------------------------
# Win detection (all four orientations, at exactly five)
# ---------------------------------------------------------------------------

def test_horizontal_win() -> None:
    board = _with(_empty_board(), _run(7, 3, 0, 1, 5, G.HUMAN))
    check(G.check_winner(board) == G.HUMAN, "five in a row horizontally is a win")


def test_vertical_win() -> None:
    board = _with(_empty_board(), _run(2, 6, 1, 0, 5, G.AI))
    check(G.check_winner(board) == G.AI, "five stacked vertically is a win")


def test_diagonal_down_right_win() -> None:
    board = _with(_empty_board(), _run(1, 1, 1, 1, 5, G.HUMAN))
    check(G.check_winner(board) == G.HUMAN, "five on a down-right diagonal is a win")


def test_diagonal_down_left_win() -> None:
    board = _with(_empty_board(), _run(1, 13, 1, -1, 5, G.AI))
    check(G.check_winner(board) == G.AI, "five on a down-left diagonal is a win")


def test_no_false_win_at_four() -> None:
    check(G.check_winner(_empty_board()) is None, "empty board has no winner")
    four = _with(_empty_board(), _run(7, 3, 0, 1, 4, G.HUMAN))
    check(G.check_winner(four) is None, "four in a row is not a win")


def test_overline_counts() -> None:
    # Freestyle: six in a row also wins (no renju overline restriction).
    six = _with(_empty_board(), _run(7, 2, 0, 1, 6, G.HUMAN))
    check(G.check_winner(six) == G.HUMAN, "six in a row (overline) is still a win")


# ---------------------------------------------------------------------------
# Place transition
# ---------------------------------------------------------------------------

def test_place_basic() -> None:
    state = G.new_game()
    moved = G.place(state)               # places at the centre cursor
    cr, cc = B.ROWS // 2, B.COLS // 2
    check(moved.board[cr][cc] == G.HUMAN, "a stone lands at the cursor")
    check(moved.current_player == G.AI, "turn passes to the AI after a placement")
    check(moved.last_move == (cr, cc), "last_move records the placed cell")


def test_occupied_cell_rejected() -> None:
    state = G.new_game()
    state = G.place(state)               # human places at centre
    centre = (B.ROWS // 2, B.COLS // 2)
    # AI's turn now; aim at the occupied centre and try to place there.
    aimed = G.move_cursor(state, 0, 0)   # cursor already there; same object
    rejected = G.place_at(state, centre)
    check(rejected is state, "placing on an occupied cell returns the same state")
    check(aimed is state, "a no-op cursor move returns the same state")


def test_winning_placement() -> None:
    # Human has four horizontally; placing the fifth wins.
    board = _with(_empty_board(), _run(7, 3, 0, 1, 4, G.HUMAN))
    state = _state(board, G.HUMAN, cursor=(7, 7))
    won = G.place(state)
    check(won.winner == G.HUMAN, "completing five sets the winner")
    check(won.game_over, "a winning placement ends the game")


def test_draw_fills_board() -> None:
    # A formula-filled board whose longest run is four in every orientation,
    # so it has no winner; the colour at (r, c) is 1 or 2.
    def colour(r: int, c: int) -> int:
        return 1 + (((r + 2 * c) // 4) % 2)

    full = tuple(
        tuple(colour(r, c) for c in range(B.COLS)) for r in range(B.ROWS)
    )
    # Guard: the formula must yield no five-in-a-row anywhere. If a future tweak
    # breaks this, the assert fires here rather than masking the draw test.
    check(G.check_winner(full) is None, "the formula board has no five-in-a-row")

    # Open one cell and make the player's colour match the formula so refilling
    # it reproduces the same no-win board, then verify the draw.
    open_cell = (0, 0)
    player = colour(*open_cell)
    board = _with(full, [(open_cell[0], open_cell[1], B.EMPTY)])
    check(len(G.empty_cells(board)) == 1, "exactly one empty cell remains")
    state = _state(board, player, cursor=open_cell)
    drawn = G.place(state)
    check(drawn.game_over, "filling the last cell ends the game")
    check(drawn.winner == 0, "a full board with no five is a draw (winner 0)")


# ---------------------------------------------------------------------------
# Immutability
# ---------------------------------------------------------------------------

def test_place_immutability() -> None:
    state = G.new_game()
    original = state.board
    moved = G.place(state)
    check(state.board is original, "original board object is unchanged after place")
    check(moved is not state, "place returns a new state object")
    check(moved.board != original, "the new board differs from the original")


# ---------------------------------------------------------------------------
# AI behaviour
# ---------------------------------------------------------------------------

def test_ai_returns_legal_move() -> None:
    board = _with(_empty_board(), [(7, 7, G.HUMAN), (7, 8, G.AI)])
    state = _state(board, G.AI)
    pos = G.ai_move(state, random.Random(1))
    check(pos in G.empty_cells(board), "AI returns a legal empty cell")
    r, c = pos
    check(board[r][c] == B.EMPTY, "AI never returns an occupied cell")


def test_ai_first_move_is_center() -> None:
    state = G.new_game()
    state = G.GameState(  # AI to move on an empty board
        board=_empty_board(),
        current_player=G.AI,
        game_over=False,
        winner=None,
        last_move=None,
        cursor=(0, 0),
    )
    pos = G.ai_move(state, random.Random(0))
    check(pos == (B.ROWS // 2, B.COLS // 2), "AI opens in the centre on an empty board")


def test_ai_takes_immediate_win() -> None:
    # AI (2) has four horizontally with both ends open; it must complete five.
    board = _with(_empty_board(), _run(7, 5, 0, 1, 4, G.AI))
    state = _state(board, G.AI)
    pos = G.ai_move(state, random.Random(0))
    check(pos in {(7, 4), (7, 9)}, "AI plays its immediate winning cell")
    r, c = pos
    placed = G.place_at(state, pos)
    check(placed.winner == G.AI, "the AI's chosen cell actually wins")


def test_ai_blocks_immediate_loss() -> None:
    # Human (1) threatens five with an open four; the AI must block an end.
    board = _with(_empty_board(), _run(7, 5, 0, 1, 4, G.HUMAN))
    state = _state(board, G.AI)
    pos = G.ai_move(state, random.Random(0))
    check(pos in {(7, 4), (7, 9)}, "AI blocks the opponent's open four")


def test_ai_blocks_when_no_own_win() -> None:
    # Human has an open four; AI has only a scattered stone. Block beats build.
    board = _with(_empty_board(), _run(3, 3, 0, 1, 4, G.HUMAN) + [(10, 10, G.AI)])
    state = _state(board, G.AI)
    pos = G.ai_move(state, random.Random(2))
    check(pos in {(3, 2), (3, 7)}, "AI prioritises blocking the human's open four")


def test_ai_is_deterministic_with_seed() -> None:
    board = _with(_empty_board(), [(7, 7, G.HUMAN), (8, 8, G.AI), (6, 6, G.HUMAN)])
    state = _state(board, G.AI)
    a = G.ai_move(state, random.Random(42))
    b = G.ai_move(state, random.Random(42))
    check(a == b, "AI is deterministic under a seeded RNG")


# ---------------------------------------------------------------------------
# Render string composition (no TTY needed)
# ---------------------------------------------------------------------------

def test_render_builds_strings() -> None:
    from blessed import Terminal
    import render as R

    term = Terminal(force_styling=True)
    state = G.new_game()

    blines = R.board_lines(term, state)
    check(len(blines) == B.ROWS, "board_lines returns one line per row")

    panel = R.panel_lines(term, state)
    check(any("GOMOKU" in line for line in panel), "panel shows the title")

    over = G.GameState(
        board=state.board,
        current_player=G.HUMAN,
        game_over=True,
        winner=G.AI,
        last_move=(7, 7),
        cursor=(7, 7),
    )
    drawn = G.GameState(
        board=state.board,
        current_player=G.HUMAN,
        game_over=True,
        winner=0,
        last_move=(7, 7),
        cursor=(7, 7),
    )
    with redirect_stdout(io.StringIO()):
        R.draw(term, state)
        R.draw(term, over)
        R.draw(term, drawn)
    check(True, "draw() composes in-play, win, and draw frames without error")


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------

def main() -> None:
    tests = [
        test_horizontal_win,
        test_vertical_win,
        test_diagonal_down_right_win,
        test_diagonal_down_left_win,
        test_no_false_win_at_four,
        test_overline_counts,
        test_place_basic,
        test_occupied_cell_rejected,
        test_winning_placement,
        test_draw_fills_board,
        test_place_immutability,
        test_ai_returns_legal_move,
        test_ai_first_move_is_center,
        test_ai_takes_immediate_win,
        test_ai_blocks_immediate_loss,
        test_ai_blocks_when_no_own_win,
        test_ai_is_deterministic_with_seed,
        test_render_builds_strings,
    ]
    for test in tests:
        test()
    print(f"\nAll {len(tests)} test groups passed.")


if __name__ == "__main__":
    main()

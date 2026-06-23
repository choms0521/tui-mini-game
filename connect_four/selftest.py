"""Headless logic checks for the Connect Four core (no terminal required).

Run with ``python selftest.py``. Exercises win detection in all four
directions, the drop transition (landing, full-column rejection, draw),
immutability, and the minimax AI (legal moves, taking an immediate win, and
blocking the opponent's immediate win), plus render string composition, so the
game can be verified in CI or over SSH without a TTY.
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


def _b(rows: list[str]) -> G.Board:
    """Build a board from 6 rows (top to bottom) of 7 chars; '.'/'0' = empty."""
    grid = tuple(tuple(0 if ch in ".0" else int(ch) for ch in row) for row in rows)
    assert len(grid) == B.ROWS and all(len(r) == B.COLS for r in grid)
    return grid


def _state(board: G.Board, player: int = G.HUMAN) -> G.GameState:
    """Wrap a board in a fresh, in-progress GameState."""
    return G.GameState(
        board=board,
        current_player=player,
        game_over=False,
        winner=None,
        last_move=None,
    )


_EMPTY = ["0000000"] * 6


# ---------------------------------------------------------------------------
# Win detection (all four directions)
# ---------------------------------------------------------------------------

def test_horizontal_win() -> None:
    board = _b(["0000000", "0000000", "0000000", "0000000", "0000000", "1111000"])
    check(G.check_winner(board) == G.HUMAN, "four in a row horizontally is a win")


def test_vertical_win() -> None:
    board = _b(["0000000", "0000000", "1000000", "1000000", "1000000", "1000000"])
    check(G.check_winner(board) == G.HUMAN, "four stacked vertically is a win")


def test_diagonal_down_right_win() -> None:
    board = _b(["0000000", "0000000", "1000000", "0100000", "0010000", "0001000"])
    check(G.check_winner(board) == G.HUMAN, "four on a down-right diagonal is a win")


def test_diagonal_down_left_win() -> None:
    board = _b(["0000000", "0000000", "0001000", "0010000", "0100000", "1000000"])
    check(G.check_winner(board) == G.HUMAN, "four on a down-left diagonal is a win")


def test_no_winner_on_empty_or_partial() -> None:
    check(G.check_winner(_b(_EMPTY)) is None, "empty board has no winner")
    partial = _b(["0000000", "0000000", "0000000", "0000000", "0000000", "1100000"])
    check(G.check_winner(partial) is None, "three or fewer in a row is not a win")


# ---------------------------------------------------------------------------
# Drop transition
# ---------------------------------------------------------------------------

def test_drop_lands_on_bottom() -> None:
    state = G.new_game()
    moved = G.drop(state, 3)
    check(moved.board[B.ROWS - 1][3] == G.HUMAN, "a disc lands on the bottom row")
    check(moved.board[B.ROWS - 2][3] == B.EMPTY, "the cell above stays empty")
    check(moved.current_player == G.AI, "turn passes to the AI after a drop")
    check(moved.last_move == 3, "last_move records the dropped column")


def test_drop_stacks() -> None:
    state = G.new_game()
    state = G.drop(state, 3)        # human at row 5
    state = G.drop(state, 3)        # AI at row 4
    check(state.board[B.ROWS - 1][3] == G.HUMAN, "first disc on the bottom")
    check(state.board[B.ROWS - 2][3] == G.AI, "second disc stacks on top")


def test_full_column_rejected() -> None:
    board = _b(["1000000", "2000000", "1000000", "2000000", "1000000", "2000000"])
    state = _state(board, G.HUMAN)
    check(0 not in G.valid_moves(board), "a full column is not a valid move")
    check(G.drop(state, 0) is state, "dropping into a full column returns same state")


def test_out_of_play_and_winning_drop() -> None:
    # Human has three at the bottom; dropping column 3 completes four and wins.
    board = _b(["0000000", "0000000", "0000000", "0000000", "0000000", "1110000"])
    state = _state(board, G.HUMAN)
    won = G.drop(state, 3)
    check(won.winner == G.HUMAN, "completing four sets the winner")
    check(won.game_over, "a winning drop ends the game")


def test_draw_fills_board() -> None:
    # A full board with no line of four; leave the top of column 0 open.
    full_rows = ["0212121", "1212121", "2121212", "2121212", "1212121", "1212121"]
    board = _b(full_rows)
    check(G.check_winner(board) is None, "the pre-draw board has no winner")
    state = _state(board, G.HUMAN)          # placing 1 at (0,0) makes no line
    drawn = G.drop(state, 0)
    check(drawn.game_over, "filling the last cell ends the game")
    check(drawn.winner == 0, "a full board with no line is a draw (winner 0)")


# ---------------------------------------------------------------------------
# Immutability
# ---------------------------------------------------------------------------

def test_drop_immutability() -> None:
    state = G.new_game()
    original = state.board
    moved = G.drop(state, 3)
    check(state.board is original, "original board object is unchanged after drop")
    check(moved is not state, "drop returns a new state object")
    check(moved.board != original, "the new board differs from the original")


# ---------------------------------------------------------------------------
# AI behaviour
# ---------------------------------------------------------------------------

def test_ai_returns_legal_move() -> None:
    board = _b(["0000000", "0000000", "0000000", "0000000", "0000000", "1200000"])
    state = _state(board, G.AI)
    col = G.ai_move(state, random.Random(1), depth=3)
    check(col in G.valid_moves(board), "AI returns a legal column")


def test_ai_takes_immediate_win() -> None:
    # AI (2) has three at the bottom; column 3 completes the win.
    board = _b(["0000000", "0000000", "0000000", "0000000", "0000000", "2220000"])
    state = _state(board, G.AI)
    col = G.ai_move(state, random.Random(0), depth=2)
    check(col == 3, "AI plays the immediate winning column")


def test_ai_blocks_immediate_loss() -> None:
    # Human (1) threatens to complete four at column 3; AI must block there.
    board = _b(["0000000", "0000000", "0000000", "0000000", "0000000", "1110000"])
    state = _state(board, G.AI)
    col = G.ai_move(state, random.Random(0), depth=2)
    check(col == 3, "AI blocks the opponent's immediate winning column")


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
    check(any("CONNECT FOUR" in line for line in panel), "panel shows the title")

    over = G.GameState(
        board=state.board,
        current_player=G.HUMAN,
        game_over=True,
        winner=G.AI,
        last_move=3,
    )
    with redirect_stdout(io.StringIO()):
        R.draw(term, state, selected_col=3)
        R.draw(term, over, selected_col=0)
    check(True, "draw() composes in-play and game-over frames without error")


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------

def main() -> None:
    tests = [
        test_horizontal_win,
        test_vertical_win,
        test_diagonal_down_right_win,
        test_diagonal_down_left_win,
        test_no_winner_on_empty_or_partial,
        test_drop_lands_on_bottom,
        test_drop_stacks,
        test_full_column_rejected,
        test_out_of_play_and_winning_drop,
        test_draw_fills_board,
        test_drop_immutability,
        test_ai_returns_legal_move,
        test_ai_takes_immediate_win,
        test_ai_blocks_immediate_loss,
        test_render_builds_strings,
    ]
    for test in tests:
        test()
    print(f"\nAll {len(tests)} test groups passed.")


if __name__ == "__main__":
    main()

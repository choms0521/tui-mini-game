"""Headless logic checks for the Reversi core (no terminal required).

Run with ``python selftest.py``. Exercises the initial setup, legal-move and
outflanking rules (including a multi-direction flip), passing and game-over
conditions, winner-by-count (including a draw), immutability, the minimax AI
(legal moves, deterministic choice, taking a corner), and render string
composition, so the game can be verified in CI or over SSH without a TTY.
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
    """Build a board from 8 rows of 8 chars; '.'/'0' = empty, '1'/'2' = discs."""
    grid = tuple(tuple(0 if ch in ".0" else int(ch) for ch in row) for row in rows)
    assert len(grid) == B.SIZE and all(len(r) == B.SIZE for r in grid)
    return grid


def _state(board: G.Board, player: int = G.HUMAN) -> G.GameState:
    """Wrap a board in a fresh, in-progress GameState."""
    return G.GameState(
        board=board,
        current_player=player,
        game_over=False,
        winner=None,
        last_move=None,
        cursor=(0, 0),
    )


# ---------------------------------------------------------------------------
# Initial setup
# ---------------------------------------------------------------------------

def test_initial_setup() -> None:
    state = G.new_game()
    check(state.board[3][3] == B.WHITE, "(3,3) starts white")
    check(state.board[4][4] == B.WHITE, "(4,4) starts white")
    check(state.board[3][4] == B.BLACK, "(3,4) starts black")
    check(state.board[4][3] == B.BLACK, "(4,3) starts black")
    check(G.disc_counts(state.board) == (2, 2), "two discs each at the start")
    check(state.current_player == G.HUMAN, "black (human) moves first")


# ---------------------------------------------------------------------------
# Legal moves and outflanking
# ---------------------------------------------------------------------------

def test_initial_legal_moves() -> None:
    state = G.new_game()
    moves = set(G.legal_moves(state.board, G.BLACK))
    expected = {(2, 3), (3, 2), (4, 5), (5, 4)}
    check(moves == expected, "black has exactly the four standard opening moves")


def test_non_outflanking_rejected() -> None:
    board = G.new_game().board
    # (0,0) is far from any disc and outflanks nothing.
    check(G.flips_for_move(board, (0, 0), G.BLACK) == [], "isolated cell is illegal")
    # The centre cells are occupied, so they cannot be played onto.
    check(G.flips_for_move(board, (3, 3), G.BLACK) == [], "occupied cell is illegal")
    check((0, 0) not in G.legal_moves(board, G.BLACK), "legal_moves omits non-outflanking cells")
    # Out-of-range positions are rejected as illegal (empty flips) rather than
    # raising IndexError or silently wrapping on a negative index.
    check(G.flips_for_move(board, (-1, 0), G.BLACK) == [], "negative row is illegal, not a wrap")
    check(G.flips_for_move(board, (B.SIZE, 0), G.BLACK) == [], "row past the edge is illegal, not a crash")
    check(G.flips_for_move(board, (0, B.SIZE), G.BLACK) == [], "col past the edge is illegal, not a crash")
    # place() honors the same contract: an out-of-range move returns the same state.
    state = G.new_game()
    check(G.place(state, (B.SIZE, B.SIZE)) is state, "place() rejects an out-of-range move unchanged")


def test_single_direction_flip() -> None:
    state = G.new_game()
    moved = G.place(state, (2, 3))  # outflanks the white at (3,3)
    check(moved.board[2][3] == G.BLACK, "placed disc is black")
    check(moved.board[3][3] == G.BLACK, "the outflanked white at (3,3) flips to black")
    check(G.disc_counts(moved.board) == (4, 1), "black gains the placed disc plus one flip")


def test_multi_direction_flip() -> None:
    # Black plays (4,4); it outflanks white at (4,3) [leftward, capped by black
    # at (4,2)] and white at (3,4) [upward, capped by black at (2,4)]. Both
    # directions flip from a single placement.
    board = _b([
        "00000000",
        "00000000",
        "00001000",
        "00002000",
        "00120000",
        "00000000",
        "00000000",
        "00000000",
    ])
    flips = set(G.flips_for_move(board, (4, 4), G.BLACK))
    check((4, 3) in flips, "leftward white is flipped")
    check((3, 4) in flips, "upward white is flipped")
    check(len(flips) == 2, "exactly the two outflanked discs flip")
    moved = G.place(_state(board, G.BLACK), (4, 4))
    check(moved.board[4][3] == G.BLACK and moved.board[3][4] == G.BLACK,
          "both directions are recolored after placement")


# ---------------------------------------------------------------------------
# Passing, game over, and winner by count
# ---------------------------------------------------------------------------

def test_pass_when_no_move() -> None:
    # An almost-full board with two empty cells, each a black-only outflank.
    # White has no legal move anywhere, so after black plays (0,0) the turn must
    # return to black (white auto-passes) while (7,7) keeps the game going.
    board = _b([
        "02211111",
        "11111111",
        "11111111",
        "11111111",
        "11111111",
        "11111111",
        "11111111",
        "11111220",
    ])
    check(G.legal_moves(board, G.WHITE) == [], "white has no legal move here")
    check((0, 0) in G.legal_moves(board, G.BLACK), "black can still move")
    moved = G.place(_state(board, G.BLACK), (0, 0))
    check(moved.current_player == G.BLACK, "black keeps the turn after white passes")
    check(not moved.game_over, "the game continues while black can move")


def test_game_over_both_pass() -> None:
    # A completely full board: neither side can move, so it is already terminal.
    full = _b(["11111111"] * 7 + ["11111112"])
    check(G.legal_moves(full, G.BLACK) == [], "no black moves on a full board")
    check(G.legal_moves(full, G.WHITE) == [], "no white moves on a full board")
    # Drive game-over through a real placement: black fills the one empty cell at
    # (0,0), outflanking the white run, which leaves the board full and ends it.
    board = _b([
        "02211111",
        "11111111",
        "11111111",
        "11111111",
        "11111111",
        "11111111",
        "11111111",
        "11111111",
    ])
    moved = G.place(_state(board, G.BLACK), (0, 0))
    check(moved.game_over, "filling the last cell with no moves left ends the game")
    check(moved.winner == G.BLACK, "the fuller side wins when the game ends")


def test_winner_by_count() -> None:
    black_heavy = _b(["11111111"] * 7 + ["11111122"])
    check(G._winner_by_count(black_heavy) == G.BLACK, "more black discs wins for black")
    white_heavy = _b(["22222222"] * 7 + ["22222211"])
    check(G._winner_by_count(white_heavy) == G.WHITE, "more white discs wins for white")
    draw = _b(["11111111"] * 4 + ["22222222"] * 4)
    check(G._winner_by_count(draw) == 0, "equal discs is a draw (winner 0)")


# ---------------------------------------------------------------------------
# Immutability
# ---------------------------------------------------------------------------

def test_place_immutability() -> None:
    state = G.new_game()
    original = state.board
    moved = G.place(state, (2, 3))
    check(state.board is original, "original board object is unchanged after place")
    check(moved is not state, "place returns a new state object")
    check(moved.board != original, "the new board differs from the original")


# ---------------------------------------------------------------------------
# AI behaviour
# ---------------------------------------------------------------------------

def test_ai_returns_legal_move() -> None:
    state = G.new_game()
    ai_state = G.GameState(
        board=state.board, current_player=G.AI, game_over=False,
        winner=None, last_move=None, cursor=(0, 0),
    )
    pos = G.ai_move(ai_state, random.Random(1), depth=2)
    check(pos in G.legal_moves(state.board, G.AI), "AI returns a legal move")


def test_ai_deterministic() -> None:
    state = G.new_game()
    ai_state = G.GameState(
        board=state.board, current_player=G.AI, game_over=False,
        winner=None, last_move=None, cursor=(0, 0),
    )
    a = G.ai_move(ai_state, random.Random(7), depth=3)
    b = G.ai_move(ai_state, random.Random(7), depth=3)
    check(a == b, "AI is deterministic given the same seeded RNG")


def test_ai_takes_corner() -> None:
    # White (AI) can play (0,0): it outflanks the black at (0,1), capped by white
    # at (0,2). The corner is by far the most valuable square, and the central
    # alternatives are worth far less, so the AI takes the corner.
    board = _b([
        "01200000",
        "00000000",
        "00000000",
        "00021000",
        "00012000",
        "00000000",
        "00000000",
        "00000000",
    ])
    ai_state = _state(board, G.AI)
    check((0, 0) in G.legal_moves(board, G.AI), "the corner is available to the AI")
    pos = G.ai_move(ai_state, random.Random(0), depth=3)
    check(pos == (0, 0), "AI takes an available corner (positional preference)")


# ---------------------------------------------------------------------------
# Render string composition (no TTY needed)
# ---------------------------------------------------------------------------

def test_render_builds_strings() -> None:
    from blessed import Terminal
    import render as R

    term = Terminal(force_styling=True)
    state = G.new_game()

    blines = R.board_lines(term, state)
    check(len(blines) == B.SIZE, "board_lines returns one line per row")

    panel = R.panel_lines(term, state)
    check(any("REVERSI" in line for line in panel), "panel shows the title")
    check(len(panel) == R.PANEL_HEIGHT, "panel pads to a fixed height without a pass notice")

    # When the side that is not to move has no legal move, the panel surfaces it.
    no_white = _b([
        "02211111",
        "11111111",
        "11111111",
        "11111111",
        "11111111",
        "11111111",
        "11111111",
        "11111220",
    ])
    pass_state = _state(no_white, G.BLACK)  # black to move; white has no move
    pass_panel = R.panel_lines(term, pass_state)
    check(any("passes" in line for line in pass_panel), "panel surfaces a pass notice")
    # Same fixed height with the notice present, so a shrinking panel leaves no
    # stale control lines behind between frames.
    check(len(pass_panel) == R.PANEL_HEIGHT, "panel keeps the fixed height with a pass notice")

    over = G.GameState(
        board=state.board, current_player=G.HUMAN, game_over=True,
        winner=G.AI, last_move=(2, 3), cursor=(3, 3),
    )
    with redirect_stdout(io.StringIO()):
        R.draw(term, state)
        R.draw(term, over)
    check(True, "draw() composes in-play and game-over frames without error")


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------

def main() -> None:
    tests = [
        test_initial_setup,
        test_initial_legal_moves,
        test_non_outflanking_rejected,
        test_single_direction_flip,
        test_multi_direction_flip,
        test_pass_when_no_move,
        test_game_over_both_pass,
        test_winner_by_count,
        test_place_immutability,
        test_ai_returns_legal_move,
        test_ai_deterministic,
        test_ai_takes_corner,
        test_render_builds_strings,
    ]
    for test in tests:
        test()
    print(f"\nAll {len(tests)} test groups passed.")


if __name__ == "__main__":
    main()

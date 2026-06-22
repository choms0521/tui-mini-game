"""Headless logic checks for the 2048 core (no terminal required).

Run with ``python selftest.py``.  Exercises slide-merge correctness, spawn
behaviour, game-over and win detection, immutability, and render string
composition — all without a real TTY.
"""
from __future__ import annotations

import contextlib
import io
import random

import board as B
import game as G


def check(condition: bool, label: str) -> None:
    if not condition:
        raise AssertionError(f"FAILED: {label}")
    print(f"ok - {label}")


# ---------------------------------------------------------------------------
# board-level tests
# ---------------------------------------------------------------------------

def test_slide_line_basic() -> None:
    """[2,2,0,0] left -> [4,0,0,0], score +4."""
    row = (2, 2, 0, 0)
    result, gained = B._slide_line(row)
    check(result == (4, 0, 0, 0), "[2,2,0,0] slides to [4,0,0,0]")
    check(gained == 4, "gained score is 4")


def test_slide_line_gap() -> None:
    """[2,0,2,0] left -> [4,0,0,0]."""
    result, gained = B._slide_line((2, 0, 2, 0))
    check(result == (4, 0, 0, 0), "[2,0,2,0] slides to [4,0,0,0]")
    check(gained == 4, "gained score is 4")


def test_slide_line_no_triple_merge() -> None:
    """[2,2,2,0] left -> [4,2,0,0]: only the first pair merges."""
    result, gained = B._slide_line((2, 2, 2, 0))
    check(result == (4, 2, 0, 0), "[2,2,2,0] slides to [4,2,0,0]")
    check(gained == 4, "no triple-merge: score is 4 not 8")


def test_slide_line_double_merge() -> None:
    """[4,4,4,4] left -> [8,8,0,0]: two independent merges."""
    result, gained = B._slide_line((4, 4, 4, 4))
    check(result == (8, 8, 0, 0), "[4,4,4,4] slides to [8,8,0,0]")
    check(gained == 16, "two merges of 4+4 each yield total score 16")


def test_slide_left_grid() -> None:
    """slide_left works across all rows of a grid."""
    grid = (
        (2, 2, 0, 0),
        (0, 4, 0, 4),
        (0, 0, 0, 0),
        (2, 2, 2, 2),
    )
    new_grid, score = B.slide_left(grid)
    check(new_grid[0] == (4, 0, 0, 0), "row 0 merges correctly")
    check(new_grid[1] == (8, 0, 0, 0), "row 1 merges correctly")
    check(new_grid[2] == (0, 0, 0, 0), "empty row stays empty")
    check(new_grid[3] == (4, 4, 0, 0), "row 3 double-merge")
    check(score == 4 + 8 + 0 + 8, "total score sums across all rows")


def test_slide_right_reversal() -> None:
    """slide_right is the mirror of slide_left."""
    row_grid = ((2, 0, 2, 0), (0, 0, 0, 0), (0, 0, 0, 0), (0, 0, 0, 0))
    left_g, _ = B.slide_left(row_grid)
    right_g, _ = B.slide_right(row_grid)
    check(left_g[0] == (4, 0, 0, 0), "left result is (4,0,0,0)")
    check(right_g[0] == (0, 0, 0, 4), "right result is (0,0,0,4)")


def test_slide_up_down() -> None:
    """slide_up and slide_down use transpose correctly."""
    grid = (
        (2, 0, 0, 0),
        (2, 0, 0, 0),
        (0, 0, 0, 0),
        (0, 0, 0, 0),
    )
    up_g, up_score = B.slide_up(grid)
    check(up_g[0][0] == 4, "slide_up merges column 0 to row 0")
    check(up_g[1][0] == 0, "row 1 col 0 is empty after slide_up")
    check(up_score == 4, "slide_up score is 4")

    dn_g, dn_score = B.slide_down(grid)
    check(dn_g[3][0] == 4, "slide_down merges column 0 to row 3")
    check(dn_score == 4, "slide_down score is 4")


def test_no_change_move() -> None:
    """A slide that cannot change the board returns the same state object."""
    rng = random.Random(42)
    state = G.new_game(rng)
    # Construct a board where no left-slide can change anything.
    grid = (
        (2, 4, 8, 16),
        (32, 64, 128, 256),
        (2, 4, 8, 16),
        (32, 64, 128, 256),
    )
    stuck_state = G.GameState(grid=grid)
    result = G.move(stuck_state, "left", rng)
    check(result is stuck_state, "no-change move returns the identical state object")


def test_spawn_only_on_change() -> None:
    """A real move spawns exactly one new tile; a no-op spawns none."""
    rng = random.Random(7)
    grid = (
        (2, 0, 0, 0),
        (0, 0, 0, 0),
        (0, 0, 0, 0),
        (0, 0, 0, 0),
    )
    state = G.GameState(grid=grid)
    # left slide: the 2 is already at col 0 — no change.
    no_change = G.move(state, "left", rng)
    check(no_change is state, "no-change move on already-left-aligned tile returns same object")

    # right slide changes the board; one new tile should appear.
    changed = G.move(state, "right", rng)
    before_count = sum(1 for r in range(B.SIZE) for c in range(B.SIZE) if grid[r][c])
    after_count = sum(1 for r in range(B.SIZE) for c in range(B.SIZE) if changed.grid[r][c])
    check(after_count == before_count + 1, "exactly one new tile spawned after a real move")


def test_game_over_detection() -> None:
    """A full board with no possible merges is detected as game-over."""
    # Checkerboard of alternating 2/4 — no adjacent equal tiles.
    grid = tuple(
        tuple(2 if (r + c) % 2 == 0 else 4 for c in range(B.SIZE))
        for r in range(B.SIZE)
    )
    check(B.is_stuck(grid), "alternating 2/4 full board is stuck")

    rng = random.Random(99)
    state = G.GameState(grid=grid)
    # Any move should set game_over (the slide won't change the board, but
    # we verify via is_stuck directly above; game_over is set post-spawn).
    # Actually a stuck board: slide returns same grid, so state object is same.
    result = G.move(state, "up", rng)
    check(result is state, "no-op move on stuck board returns same object")
    # Manually set game_over via is_stuck.
    check(B.is_stuck(state.grid), "is_stuck correctly flags the board")


def test_win_detection() -> None:
    """Reaching 2048 sets won=True; it stays True even after further moves."""
    rng = random.Random(11)
    # Place a 1024 tile in a mergeable position.
    grid = (
        (1024, 1024, 0, 0),
        (0,    0,    0, 0),
        (0,    0,    0, 0),
        (0,    0,    0, 0),
    )
    state = G.GameState(grid=grid)
    result = G.move(state, "left", rng)
    check(result.won, "merging two 1024 tiles sets won=True")
    check(any(result.grid[r][c] >= 2048 for r in range(B.SIZE) for c in range(B.SIZE)),
          "a 2048 tile is present in the grid")

    # Won flag is sticky.
    result2 = G.move(result, "right", rng)
    check(result2.won, "won flag remains True after subsequent moves")


def test_immutability() -> None:
    """Applying a move does not alter the original state."""
    rng = random.Random(55)
    grid = (
        (2, 0, 0, 0),
        (0, 0, 0, 0),
        (0, 0, 0, 0),
        (0, 0, 0, 0),
    )
    original = G.GameState(grid=grid)
    original_grid_copy = tuple(tuple(row) for row in original.grid)
    _ = G.move(original, "right", rng)
    check(original.grid == original_grid_copy, "original grid is untouched after move")


def test_new_game_has_two_tiles() -> None:
    """new_game seeds the board with exactly two tiles."""
    rng = random.Random(123)
    state = G.new_game(rng)
    count = sum(1 for r in range(B.SIZE) for c in range(B.SIZE) if state.grid[r][c])
    check(count == 2, "new_game places exactly two tiles")


def test_render_draw() -> None:
    """draw() composes a complete frame without raising — no real TTY needed."""
    import render as R
    from blessed import Terminal

    term = Terminal(force_styling=True)
    rng = random.Random(77)
    state = G.new_game(rng)

    b_lines = R.board_lines(term, state)
    check(len(b_lines) == B.SIZE * 2 + 1, "board_lines has SIZE*2+1 rows (cells + separators)")

    p_lines = R.panel_lines(term, state)
    check(any("2048" in line for line in p_lines), "panel shows title GAME 2048")

    # draw() must not raise for normal, won, and game-over states.
    won_state = G.GameState(grid=state.grid, score=0, won=True, game_over=False)
    over_state = G.GameState(grid=state.grid, score=0, won=False, game_over=True)
    with contextlib.redirect_stdout(io.StringIO()):
        R.draw(term, state)
        R.draw(term, won_state)
        R.draw(term, over_state)
    check(True, "draw() composes normal, won, and game-over frames without error")


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------

def main() -> None:
    tests = [
        test_slide_line_basic,
        test_slide_line_gap,
        test_slide_line_no_triple_merge,
        test_slide_line_double_merge,
        test_slide_left_grid,
        test_slide_right_reversal,
        test_slide_up_down,
        test_no_change_move,
        test_spawn_only_on_change,
        test_game_over_detection,
        test_win_detection,
        test_immutability,
        test_new_game_has_two_tiles,
        test_render_draw,
    ]
    for test in tests:
        test()
    print(f"\nAll {len(tests)} test groups passed.")


if __name__ == "__main__":
    main()

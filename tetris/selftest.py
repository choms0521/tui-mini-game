"""Headless logic checks for the Tetris core (no terminal required).

Run with ``python selftest.py``. Exercises rotation, collision, movement,
line clearing, scoring, and the rendering string builder so the game can be
verified in CI or over SSH where no interactive TTY is available.
"""
from __future__ import annotations

import random

import board as B
import game as G
import pieces as P


def check(condition: bool, label: str) -> None:
    if not condition:
        raise AssertionError(f"FAILED: {label}")
    print(f"ok - {label}")


def test_rotation_round_trip() -> None:
    for name, matrix in P.SHAPES.items():
        spun = P.rotate_cw(P.rotate_cw(P.rotate_cw(P.rotate_cw(matrix))))
        check(spun == matrix, f"{name} returns to itself after four CW turns")
        check(P.rotate_ccw(matrix) == P.rotate_cw(P.rotate_cw(P.rotate_cw(matrix))),
              f"{name} CCW equals three CW turns")


def test_occupied_counts() -> None:
    for name, matrix in P.SHAPES.items():
        check(len(P.occupied_cells(matrix)) == 4, f"{name} has exactly 4 cells")


def test_collision_and_bounds() -> None:
    grid = B.empty_grid()
    check(B.fits(grid, [(0, 0), (19, 9)]), "corner cells fit on empty grid")
    check(not B.fits(grid, [(0, -1)]), "off the left wall does not fit")
    check(not B.fits(grid, [(0, B.WIDTH)]), "off the right wall does not fit")
    check(not B.fits(grid, [(B.HEIGHT, 0)]), "below the floor does not fit")
    check(B.fits(grid, [(-1, 0)]), "above the top is allowed")


def test_place_is_immutable() -> None:
    grid = B.empty_grid()
    placed = B.place(grid, [(19, 0)], "T")
    check(grid[19][0] is None, "original grid is untouched after place")
    check(placed[19][0] == "T", "new grid records the placed cell")


def test_line_clear_and_gravity() -> None:
    width = B.WIDTH
    full_row = tuple("X" for _ in range(width))
    above = tuple([None] * (width - 1) + ["Z"])
    grid = tuple([above] + [full_row] + [tuple([None] * width)] * (B.HEIGHT - 2))
    cleared_grid, count = B.clear_lines(grid)
    check(count == 1, "exactly one full row cleared")
    check(len(cleared_grid) == B.HEIGHT, "grid height preserved after clear")
    check(cleared_grid[0] == tuple([None] * width), "a new empty row appears on top")
    check(cleared_grid[1] == above, "rows above the cleared line fall down by one")


def test_move_and_blocked() -> None:
    rng = random.Random(1)
    state = G.new_game(rng)
    start_col = state.active.col
    moved = G.try_move(state, 0, -1)
    check(moved.active.col == start_col - 1, "piece moves left when there is room")

    far_left = state
    for _ in range(B.WIDTH):
        far_left = G.try_move(far_left, 0, -1)
    blocked = G.try_move(far_left, 0, -1)
    check(blocked is far_left, "blocked move returns the same state object")


def test_hard_drop_locks_and_scores() -> None:
    rng = random.Random(2)
    state = G.new_game(rng)
    first_name = state.active.name
    dropped = G.hard_drop(state, rng)
    check(dropped.score > 0, "hard drop awards points")
    check(dropped.active.name != first_name or dropped.bag != state.bag,
          "a new active piece is spawned after locking")
    filled = sum(1 for row in dropped.grid for cell in row if cell is not None)
    check(filled == 4, "exactly one piece (4 cells) is locked into the grid")


def test_lock_completes_and_scores_line() -> None:
    rng = random.Random(5)
    base = G.new_game(rng)
    width = B.WIDTH
    rows = [tuple([None] * width) for _ in range(B.HEIGHT)]
    # Bottom row full except columns 4 and 5; an O piece will complete it.
    rows[B.HEIGHT - 1] = tuple(None if c in (4, 5) else "X" for c in range(width))
    active = G.Active(name="O", matrix=P.SHAPES["O"], row=B.HEIGHT - 2, col=4)
    state = G.GameState(grid=tuple(rows), active=active, bag=base.bag)

    locked = G._lock(state, rng)
    check(locked.lines == 1, "completing a row increments the line count")
    check(locked.score == 100, "a single line scores 100 at level 1")
    check(len(locked.grid) == B.HEIGHT, "grid height is preserved after a clear")
    filled = sum(1 for row in locked.grid for cell in row if cell is not None)
    check(filled == 2, "only the leftover O cells remain after the row clears")
    check(
        locked.grid[B.HEIGHT - 1][4] == "O" and locked.grid[B.HEIGHT - 1][5] == "O",
        "leftover cells fall to the bottom row after the clear",
    )
    check(not locked.game_over, "clearing a line does not end the game")


def test_game_over_detection() -> None:
    rng = random.Random(3)
    state = G.new_game(rng)
    # Leave the last column empty so no row can clear, while the spawn point at
    # the top-centre stays blocked. Locking must then end the game.
    almost_full = tuple(
        tuple("X" if c < B.WIDTH - 1 else None for c in range(B.WIDTH))
        for _ in range(B.HEIGHT)
    )
    state = G.GameState(grid=almost_full, active=state.active, bag=state.bag)
    over = G._lock(state, rng)
    check(over.game_over, "locking with no room to spawn ends the game")


def test_render_builds_strings() -> None:
    import io
    from contextlib import redirect_stdout

    from blessed import Terminal
    import render as R

    term = Terminal(force_styling=True)
    rng = random.Random(4)
    state = G.new_game(rng)
    board = R.board_lines(term, state)
    check(len(board) == B.HEIGHT + 2, "board renders all rows plus two borders")
    panel = R.panel_lines(term, state)
    check(any("TETRIS" in line for line in panel), "panel shows the title")

    # draw() must compose a full frame without raising, including overlays.
    over_state = G.GameState(
        grid=state.grid, active=state.active, bag=state.bag, game_over=True
    )
    with redirect_stdout(io.StringIO()):
        R.draw(term, state, paused=False)
        R.draw(term, state, paused=True)
        R.draw(term, over_state)
    check(True, "draw() composes normal, paused, and game-over frames without error")


def main() -> None:
    tests = [
        test_rotation_round_trip,
        test_occupied_counts,
        test_collision_and_bounds,
        test_place_is_immutable,
        test_line_clear_and_gravity,
        test_move_and_blocked,
        test_hard_drop_locks_and_scores,
        test_lock_completes_and_scores_line,
        test_game_over_detection,
        test_render_builds_strings,
    ]
    for test in tests:
        test()
    print(f"\nAll {len(tests)} test groups passed.")


if __name__ == "__main__":
    main()

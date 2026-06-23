"""Headless logic checks for the Sudoku core (no terminal required).

Run with ``python selftest.py``. Exercises the solver, uniqueness checker,
puzzle generator, board validity/conflict helpers, the state transitions,
win detection, immutability, and the rendering string builder so the game can
be verified in CI or over SSH without a TTY.

The test set is deterministic (fixed seeds) and fast: generation is checked
with a high given count so cell removal stays cheap, and the uniqueness search
early-exits at the second solution.
"""
from __future__ import annotations

import io
import random
from contextlib import redirect_stdout
from dataclasses import replace

import board as B
import game as G
import render as R
import solver as S


def check(condition: bool, label: str) -> None:
    if not condition:
        raise AssertionError(f"FAILED: {label}")
    print(f"ok - {label}")


def _to_grid(rows: list[str]) -> B.Grid:
    """Build an immutable grid from rows of digit strings ('.' or '0' = blank)."""
    return tuple(
        tuple(0 if ch in ".0" else int(ch) for ch in row)
        for row in rows
    )


# A known proper puzzle and its unique solution (a standard easy board).
_PUZZLE_ROWS = [
    "53..7....",
    "6..195...",
    ".98....6.",
    "8...6...3",
    "4..8.3..1",
    "7...2...6",
    ".6....28.",
    "...419..5",
    "....8..79",
]
_SOLUTION_ROWS = [
    "534678912",
    "672195348",
    "198342567",
    "859761423",
    "426853791",
    "713924856",
    "961537284",
    "287419635",
    "345286179",
]
_KNOWN_PUZZLE = _to_grid(_PUZZLE_ROWS)
_KNOWN_SOLUTION = _to_grid(_SOLUTION_ROWS)


# ---------------------------------------------------------------------------
# Board helpers
# ---------------------------------------------------------------------------

def test_bounds_and_cells() -> None:
    check(B.in_bounds(0, 0), "top-left corner is in bounds")
    check(B.in_bounds(B.SIZE - 1, B.SIZE - 1), "bottom-right corner is in bounds")
    check(not B.in_bounds(-1, 0), "row -1 is out of bounds")
    check(not B.in_bounds(0, B.SIZE), "col == SIZE is out of bounds")
    cells = B.all_cells()
    check(len(cells) == B.SIZE * B.SIZE, "all_cells() returns SIZE*SIZE entries")
    check(cells == sorted(cells), "all_cells() is in sorted (row-major) order")


def test_box_helpers() -> None:
    check(B.box_origin(0, 0) == (0, 0), "box origin of (0,0) is (0,0)")
    check(B.box_origin(5, 7) == (3, 6), "box origin of (5,7) is (3,6)")
    box = B.box_cells(4, 4)
    check(len(box) == B.BOX * B.BOX, "box_cells returns 9 cells")
    check((3, 3) in box and (5, 5) in box, "box_cells covers the centre box")


def test_peers() -> None:
    p = B.peers(0, 0)
    # 8 in the row + 8 in the col + 4 extra in the box, all distinct = 20.
    check(len(p) == 20, "a cell has exactly 20 peers")
    check((0, 0) not in p, "a cell is not its own peer")
    check((0, 8) in p and (8, 0) in p, "row and column peers are present")
    check((1, 1) in p, "box peer (1,1) is present")


# ---------------------------------------------------------------------------
# Validity / conflicts
# ---------------------------------------------------------------------------

def test_is_legal_row_col_box() -> None:
    grid = _KNOWN_PUZZLE
    # Row 0 already has a 5 and a 3; placing 5 elsewhere in row 0 is illegal.
    check(not B.is_legal(grid, 0, 2, 5), "duplicate in row is illegal")
    # Column 0 has 5,6,8,4,7; placing 6 at (2,0) duplicates the column.
    check(not B.is_legal(grid, 2, 0, 6), "duplicate in column is illegal")
    # Top-left box has 5,3,6,9,8; placing 9 at (0,2) duplicates the box.
    check(not B.is_legal(grid, 0, 2, 9), "duplicate in box is illegal")
    # 1 fits at (0,2): not in its row, column, or box.
    check(B.is_legal(grid, 0, 2, 1), "a non-conflicting digit is legal")
    check(B.is_legal(grid, 0, 2, B.EMPTY), "EMPTY is always legal")


def test_conflict_detection() -> None:
    grid = _to_grid(_SOLUTION_ROWS)
    check(len(B.conflicts(grid)) == 0, "a valid full grid has no conflicts")

    # Inject a duplicate 5 into the second cell of row 0 (col 0 is already 5).
    bad_rows = list(_SOLUTION_ROWS)
    bad_rows[0] = "5" + "5" + bad_rows[0][2:]
    bad = _to_grid(bad_rows)
    conflict = B.conflicts(bad)
    check((0, 0) in conflict and (0, 1) in conflict,
          "both members of a row duplicate are flagged as conflicts")


def test_is_complete() -> None:
    check(B.is_complete(_KNOWN_SOLUTION), "the full valid solution is complete")
    check(not B.is_complete(_KNOWN_PUZZLE), "a puzzle with blanks is not complete")


# ---------------------------------------------------------------------------
# Solver
# ---------------------------------------------------------------------------

def test_solver_finds_known_solution() -> None:
    solved = S.solve(_KNOWN_PUZZLE)
    check(solved == _KNOWN_SOLUTION, "solver reaches the known unique solution")


def test_solver_fills_blank_grid() -> None:
    rng = random.Random(7)
    full = S.generate_full(rng)
    check(B.is_complete(full), "generate_full returns a complete valid grid")


def test_solver_unsolvable_returns_none() -> None:
    # Take the known solution, blank (0,0), and change (0,8) from 2 to 5.
    # Row 0 now already holds a 5, so the single empty cell (0,0) has no legal
    # digit and the solver fails immediately (a cheaply unsolvable grid).
    rows = list(_SOLUTION_ROWS)
    rows[0] = "0" + rows[0][1:8] + "5"
    grid = _to_grid(rows)
    check(S.solve(grid) is None, "solver returns None for an unsolvable grid")


# ---------------------------------------------------------------------------
# Uniqueness checker
# ---------------------------------------------------------------------------

def test_uniqueness_proper_puzzle() -> None:
    check(S.count_solutions(_KNOWN_PUZZLE) == 1,
          "a proper puzzle has exactly one solution")
    check(S.has_unique_solution(_KNOWN_PUZZLE),
          "has_unique_solution is True for a proper puzzle")


def test_uniqueness_underconstrained() -> None:
    # The known solution with the first two rows (one full band) blanked is
    # under-constrained: those 18 cells admit more than one completion.
    rows = ["." * 9, "." * 9] + _SOLUTION_ROWS[2:]
    loose = _to_grid(rows)
    count = S.count_solutions(loose, limit=2)
    check(count >= 2, "an under-constrained puzzle reports 2+ solutions")
    check(not S.has_unique_solution(loose),
          "has_unique_solution is False when multiple solutions exist")


def test_uniqueness_early_exit_caps_count() -> None:
    # An empty grid has billions of solutions; the cap must stop the search.
    blank = _to_grid(["." * 9 for _ in range(9)])
    count = S.count_solutions(blank, limit=2)
    check(count == 2, "count_solutions caps at the limit (early exit)")


# ---------------------------------------------------------------------------
# Generator
# ---------------------------------------------------------------------------

def test_generated_puzzle_is_proper() -> None:
    # Use a high given count so cell removal stays cheap and fast.
    rng = random.Random(123)
    puzzle, solution = S.generate_puzzle(rng, givens=60)
    check(B.is_complete(solution), "generated solution is complete and valid")
    check(S.has_unique_solution(puzzle),
          "generated puzzle has a unique solution")
    solved = S.solve(puzzle)
    check(solved == solution, "generated puzzle solves to its own solution")
    # Every given must agree with the solution.
    agree = all(
        puzzle[r][c] in (B.EMPTY, solution[r][c])
        for r in range(B.SIZE) for c in range(B.SIZE)
    )
    check(agree, "every given matches the solution")


def test_generation_deterministic() -> None:
    p1, s1 = S.generate_puzzle(random.Random(999), givens=60)
    p2, s2 = S.generate_puzzle(random.Random(999), givens=60)
    check(p1 == p2 and s1 == s2,
          "generation is deterministic for a fixed seed")


# ---------------------------------------------------------------------------
# Game state transitions
# ---------------------------------------------------------------------------

def _known_state() -> G.GameState:
    """Build a GameState directly from the known puzzle/solution (no RNG)."""
    return G.GameState(
        givens=_KNOWN_PUZZLE,
        grid=_KNOWN_PUZZLE,
        solution=_KNOWN_SOLUTION,
        cursor=(0, 0),
        won=False,
    )


def test_new_game_state() -> None:
    rng = random.Random(5)
    state = G.new_game(rng, givens=60)
    check(state.grid == state.givens, "new game starts with grid equal to givens")
    check(not state.won, "new game is not won")
    check(state.cursor == (0, 0), "cursor starts at (0,0)")
    check(S.has_unique_solution(state.givens), "new game puzzle is proper")


def test_move_cursor_clamped() -> None:
    state = _known_state()
    check(G.move_cursor(state, -1, 0) is state, "moving up at the top is a no-op")
    moved = G.move_cursor(state, 1, 0)
    check(moved.cursor == (1, 0), "moving down advances the cursor")
    check(moved is not state, "a real move returns a new state object")


def test_set_value_on_given_protected() -> None:
    state = _known_state()
    # (0,0) is a given (5); attempting to set it must be a no-op.
    check(G.is_given(state, 0, 0), "(0,0) is a given cell")
    check(G.set_value(state, 9) is state, "setting a given cell is a no-op")


def test_set_and_clear_value() -> None:
    state = _known_state()
    # (0,2) is blank in the puzzle. Move the cursor there and set a value.
    at = replace(state, cursor=(0, 2))
    filled = G.set_value(at, 1)
    check(filled.grid[0][2] == 1, "set_value writes the digit on a blank cell")
    check(filled is not at, "set_value returns a new state object")
    cleared = G.clear_value(filled)
    check(cleared.grid[0][2] == B.EMPTY, "clear_value blanks the cell again")
    check(G.clear_value(at) is at, "clearing an already-empty cell is a no-op")


def test_win_detection() -> None:
    state = _known_state()
    # Fill the whole grid to match the solution one cell at a time.
    for (r, c) in B.all_cells():
        if state.grid[r][c] == B.EMPTY:
            at = replace(state, cursor=(r, c))
            state = G.set_value(at, _KNOWN_SOLUTION[r][c])
    check(state.grid == _KNOWN_SOLUTION, "grid matches the solution after filling")
    check(state.won, "won flag is set when grid equals solution")
    # Once won, further edits are ignored.
    check(G.set_value(state, 1) is state, "edits after winning are ignored")


def test_immutability() -> None:
    state = _known_state()
    at = replace(state, cursor=(0, 2))
    original_grid = at.grid
    _new = G.set_value(at, 1)
    check(at.grid == original_grid, "original grid is unchanged after set_value")
    check(at.grid is original_grid, "original grid object identity is preserved")


# ---------------------------------------------------------------------------
# Render string composition (no TTY needed)
# ---------------------------------------------------------------------------

def test_render_builds_strings() -> None:
    from blessed import Terminal

    term = Terminal(force_styling=True)
    state = _known_state()

    board = R.board_lines(term, state)
    # 9 cell rows + 4 horizontal rules (top, after each box) = 13 lines.
    check(len(board) == B.SIZE + B.BOX + 1, "board renders cells plus box rules")

    panel = R.panel_lines(term, state)
    check(any("SUDOKU" in line for line in panel), "panel shows the SUDOKU title")

    won_state = replace(state, won=True)
    with redirect_stdout(io.StringIO()):
        R.draw(term, state)
        R.draw(term, won_state)
    check(True, "draw() composes normal and won frames without error")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    tests = [
        test_bounds_and_cells,
        test_box_helpers,
        test_peers,
        test_is_legal_row_col_box,
        test_conflict_detection,
        test_is_complete,
        test_solver_finds_known_solution,
        test_solver_fills_blank_grid,
        test_solver_unsolvable_returns_none,
        test_uniqueness_proper_puzzle,
        test_uniqueness_underconstrained,
        test_uniqueness_early_exit_caps_count,
        test_generated_puzzle_is_proper,
        test_generation_deterministic,
        test_new_game_state,
        test_move_cursor_clamped,
        test_set_value_on_given_protected,
        test_set_and_clear_value,
        test_win_detection,
        test_immutability,
        test_render_builds_strings,
    ]
    for test in tests:
        test()
    print(f"\nAll {len(tests)} test groups passed.")


if __name__ == "__main__":
    main()

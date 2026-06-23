"""Grid dimensions and pure geometry/validity helpers for the Sudoku board.

No game logic lives here: just the constants that describe the 9x9 grid and
pure helpers that report which placements are legal. Every function is pure and
side-effect free, mirroring the role of snake/board.py and tetris/board.py.

The grid is represented throughout the game as a tuple of 9 rows, each a tuple
of 9 ints, where 0 means an empty cell and 1-9 a filled digit.
"""
from __future__ import annotations

from typing import List, Tuple

SIZE = 9        # the grid is SIZE x SIZE
BOX = 3         # each box is BOX x BOX; SIZE must equal BOX * BOX
EMPTY = 0       # sentinel value for a blank cell

Grid = Tuple[Tuple[int, ...], ...]
Cell = Tuple[int, int]


def in_bounds(row: int, col: int) -> bool:
    """True when (row, col) is a valid cell on the grid."""
    return 0 <= row < SIZE and 0 <= col < SIZE


def all_cells() -> List[Cell]:
    """Return every cell in row-major order (deterministic iteration order)."""
    return [(r, c) for r in range(SIZE) for c in range(SIZE)]


def box_origin(row: int, col: int) -> Cell:
    """Return the (row, col) of the top-left cell of the 3x3 box containing (row, col)."""
    return (row - row % BOX, col - col % BOX)


def box_cells(row: int, col: int) -> List[Cell]:
    """Return the nine cells of the 3x3 box that contains (row, col)."""
    br, bc = box_origin(row, col)
    return [(br + dr, bc + dc) for dr in range(BOX) for dc in range(BOX)]


def peers(row: int, col: int) -> List[Cell]:
    """Return all cells that share a row, column, or box with (row, col).

    The cell itself is excluded. Duplicates (the box cells that also lie on the
    same row/column) are removed so each peer appears exactly once.
    """
    seen = set()
    result: List[Cell] = []
    for c in range(SIZE):
        seen.add((row, c))
    for r in range(SIZE):
        seen.add((r, col))
    for cell in box_cells(row, col):
        seen.add(cell)
    seen.discard((row, col))
    # Return in a deterministic, row-major order.
    result = sorted(seen)
    return result


def is_legal(grid: Grid, row: int, col: int, value: int) -> bool:
    """True when placing *value* at (row, col) breaks no Sudoku constraint.

    A value already sitting in the same cell is ignored (a cell never conflicts
    with itself). EMPTY (0) is always legal because it represents a blank, while
    any value outside the 1..SIZE digit domain is always illegal.
    """
    if value == EMPTY:
        return True
    if not (1 <= value <= SIZE):
        return False  # outside the 1..SIZE digit domain — never a legal placement
    for c in range(SIZE):
        if c != col and grid[row][c] == value:
            return False
    for r in range(SIZE):
        if r != row and grid[r][col] == value:
            return False
    for (r, c) in box_cells(row, col):
        if (r, c) != (row, col) and grid[r][c] == value:
            return False
    return True


def conflicts(grid: Grid) -> frozenset[Cell]:
    """Return the set of filled cells that violate a Sudoku constraint.

    A cell is in conflict when its value is duplicated by another filled cell in
    the same row, column, or box. Empty cells are never reported. Both members
    of a duplicate pair are included so the renderer can highlight all of them.
    """
    bad: set = set()
    for (r, c) in all_cells():
        value = grid[r][c]
        if value == EMPTY:
            continue
        if not is_legal(grid, r, c, value):
            bad.add((r, c))
    return frozenset(bad)


def is_complete(grid: Grid) -> bool:
    """True when every cell is filled (no zeros) and no constraint is violated."""
    for (r, c) in all_cells():
        if grid[r][c] == EMPTY:
            return False
    return len(conflicts(grid)) == 0

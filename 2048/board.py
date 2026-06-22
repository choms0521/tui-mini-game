"""The 4x4 grid logic: sliding, merging, spawning, and end-state detection.

The grid is an immutable tuple of tuples of int (0 == empty).  Every operation
that would change the board returns a brand-new object instead of mutating the
old one.
"""
from __future__ import annotations

import random
from typing import Tuple

Grid = Tuple[Tuple[int, ...], ...]

SIZE = 4


def empty_grid() -> Grid:
    """Return a 4x4 grid filled with zeros."""
    return tuple(tuple(0 for _ in range(SIZE)) for _ in range(SIZE))


# ---------------------------------------------------------------------------
# Slide / merge helpers
# ---------------------------------------------------------------------------

def _slide_line(line: Tuple[int, ...]) -> Tuple[Tuple[int, ...], int]:
    """Slide one row/column toward index 0, merging equal adjacent tiles.

    Returns ``(new_line, score_gained)`` where *new_line* is always length
    ``SIZE``.  Each tile merges at most once per call — a triple like
    ``[2, 2, 2, 0]`` becomes ``[4, 2, 0, 0]``, not ``[8, 0, 0, 0]``.
    """
    # Compact: remove zeros.
    tiles = [v for v in line if v]
    gained = 0
    merged: list[int] = []
    i = 0
    while i < len(tiles):
        if i + 1 < len(tiles) and tiles[i] == tiles[i + 1]:
            value = tiles[i] * 2
            merged.append(value)
            gained += value
            i += 2
        else:
            merged.append(tiles[i])
            i += 1
    # Pad back to SIZE with zeros.
    while len(merged) < SIZE:
        merged.append(0)
    return tuple(merged), gained


def slide_left(grid: Grid) -> Tuple[Grid, int]:
    """Slide all rows toward the left edge.  Returns ``(new_grid, score)``."""
    total = 0
    rows = []
    for row in grid:
        new_row, gained = _slide_line(row)
        rows.append(new_row)
        total += gained
    return tuple(rows), total


def slide_right(grid: Grid) -> Tuple[Grid, int]:
    """Slide all rows toward the right edge."""
    total = 0
    rows = []
    for row in grid:
        rev, gained = _slide_line(row[::-1])
        rows.append(rev[::-1])
        total += gained
    return tuple(rows), total


def _transpose(grid: Grid) -> Grid:
    """Transpose rows and columns."""
    return tuple(tuple(grid[r][c] for r in range(SIZE)) for c in range(SIZE))


def slide_up(grid: Grid) -> Tuple[Grid, int]:
    """Slide all columns upward (toward row 0)."""
    t, score = slide_left(_transpose(grid))
    return _transpose(t), score


def slide_down(grid: Grid) -> Tuple[Grid, int]:
    """Slide all columns downward (toward row SIZE-1)."""
    t, score = slide_right(_transpose(grid))
    return _transpose(t), score


# ---------------------------------------------------------------------------
# Spawn
# ---------------------------------------------------------------------------

def empty_cells(grid: Grid) -> Tuple[Tuple[int, int], ...]:
    """Return ``(row, col)`` pairs for every zero cell."""
    return tuple(
        (r, c)
        for r in range(SIZE)
        for c in range(SIZE)
        if grid[r][c] == 0
    )


def spawn_tile(grid: Grid, rng: random.Random) -> Grid:
    """Place a 2 (90 %) or 4 (10 %) on a random empty cell.

    The caller is responsible for checking that empty cells exist before
    calling this function.
    """
    empties = empty_cells(grid)
    r, c = rng.choice(empties)
    value = 2 if rng.random() < 0.9 else 4
    rows = [list(row) for row in grid]
    rows[r][c] = value
    return tuple(tuple(row) for row in rows)


# ---------------------------------------------------------------------------
# End-state detection
# ---------------------------------------------------------------------------

def has_won(grid: Grid) -> bool:
    """True when any cell contains 2048 or higher."""
    return any(grid[r][c] >= 2048 for r in range(SIZE) for c in range(SIZE))


def is_stuck(grid: Grid) -> bool:
    """True when the board is full and no slide direction would change it."""
    if empty_cells(grid):
        return False
    for slide_fn in (slide_left, slide_right, slide_up, slide_down):
        new_grid, _ = slide_fn(grid)
        if new_grid != grid:
            return False
    return True

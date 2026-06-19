"""The playfield grid: collision checks, locking pieces, and clearing lines.

The grid is an immutable tuple of rows. Each cell is either ``None`` (empty) or
a piece-name string identifying the colour of a locked block. Every mutating
operation returns a brand new grid instead of changing the old one.
"""
from __future__ import annotations

from typing import Iterable, Optional, Tuple

Cell = Optional[str]
Grid = Tuple[Tuple[Cell, ...], ...]
Cells = Iterable[Tuple[int, int]]

WIDTH = 10
HEIGHT = 20


def empty_grid(width: int = WIDTH, height: int = HEIGHT) -> Grid:
    """Return an empty grid of the given size."""
    return tuple(tuple(None for _ in range(width)) for _ in range(height))


def fits(grid: Grid, cells: Cells) -> bool:
    """True when every cell is within the walls and lands on an empty square.

    Cells above the top edge (``row < 0``) are allowed so a piece can spawn and
    rotate while partially off-screen.
    """
    height = len(grid)
    width = len(grid[0])
    for r, c in cells:
        if c < 0 or c >= width or r >= height:
            return False
        if r < 0:
            continue
        if grid[r][c] is not None:
            return False
    return True


def place(grid: Grid, cells: Cells, name: str) -> Grid:
    """Return a new grid with ``cells`` filled by the given piece name."""
    height = len(grid)
    width = len(grid[0])
    rows = [list(row) for row in grid]
    for r, c in cells:
        if 0 <= r < height and 0 <= c < width:
            rows[r][c] = name
    return tuple(tuple(row) for row in rows)


def clear_lines(grid: Grid) -> Tuple[Grid, int]:
    """Remove every full row and return ``(new_grid, lines_cleared)``.

    Cleared rows are replaced by empty rows at the top so the stack falls down.
    """
    width = len(grid[0])
    kept = [row for row in grid if any(cell is None for cell in row)]
    cleared = len(grid) - len(kept)
    empty_rows = tuple(tuple(None for _ in range(width)) for _ in range(cleared))
    return empty_rows + tuple(kept), cleared

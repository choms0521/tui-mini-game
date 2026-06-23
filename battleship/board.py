"""Grid geometry and fleet definition for Battleship.

No game logic lives here: just the constants that describe the two 10x10
playfields, the position type, and a few pure geometry helpers (bounds checks
and orthogonal adjacency). Mirrors the role of minesweeper/board.py.
"""
from __future__ import annotations

from typing import Tuple

ROWS = 10
COLS = 10

Pos = Tuple[int, int]

# Standard fleet: (name, length). 5 ships, 17 cells total.
FLEET: Tuple[Tuple[str, int], ...] = (
    ("Carrier", 5),
    ("Battleship", 4),
    ("Cruiser", 3),
    ("Submarine", 3),
    ("Destroyer", 2),
)

# The four orthogonal directions used for AI target-mode neighbours.
ORTHO: Tuple[Pos, ...] = ((-1, 0), (1, 0), (0, -1), (0, 1))


def in_bounds(pos: Pos, rows: int = ROWS, cols: int = COLS) -> bool:
    """True when *pos* is a valid cell on the board."""
    r, c = pos
    return 0 <= r < rows and 0 <= c < cols


def neighbours(pos: Pos, rows: int = ROWS, cols: int = COLS) -> Tuple[Pos, ...]:
    """Return all in-bounds orthogonal (up/down/left/right) neighbours of *pos*."""
    r, c = pos
    return tuple(
        (r + dr, c + dc)
        for dr, dc in ORTHO
        if in_bounds((r + dr, c + dc), rows, cols)
    )


def ship_cells(start: Pos, length: int, horizontal: bool) -> Tuple[Pos, ...]:
    """Return the cells a ship of *length* occupies starting at *start*.

    A horizontal ship extends to the right (increasing column); a vertical ship
    extends downward (increasing row). The returned cells may run out of bounds;
    callers validate placement separately.
    """
    r, c = start
    if horizontal:
        return tuple((r, c + i) for i in range(length))
    return tuple((r + i, c) for i in range(length))

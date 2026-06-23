"""Grid dimensions, direction constants, and pure geometry helpers for Tron.

No game logic lives here: just the constants that describe the playfield and
helpers that check whether a position is within bounds. Every function is pure
and side-effect free, mirroring the role of snake/board.py.
"""
from __future__ import annotations

from typing import List, Tuple

WIDTH = 40   # columns of the playfield (not counting the border)
HEIGHT = 20  # rows of the playfield (not counting the border)

Pos = Tuple[int, int]

# Direction constants as (drow, dcol) unit vectors.
UP    = (-1,  0)
DOWN  = ( 1,  0)
LEFT  = ( 0, -1)
RIGHT = ( 0,  1)

DIRECTIONS = (UP, DOWN, LEFT, RIGHT)


def in_bounds(row: int, col: int) -> bool:
    """True when (row, col) is a valid cell inside the playfield."""
    return 0 <= row < HEIGHT and 0 <= col < WIDTH


def add(pos: Pos, direction: Pos) -> Pos:
    """Return the cell reached by stepping one unit in *direction*."""
    return (pos[0] + direction[0], pos[1] + direction[1])


def all_cells() -> List[Pos]:
    """Return every valid cell in row-major order (deterministic ordering)."""
    return [(r, c) for r in range(HEIGHT) for c in range(WIDTH)]

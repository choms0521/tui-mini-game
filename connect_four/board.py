"""Grid dimensions and pure geometry helpers for the Connect Four board.

No game logic lives here: just the constants that describe the playfield and a
couple of pure helpers. Mirrors the role of snake/board.py and tetris/board.py.
"""
from __future__ import annotations

from typing import Tuple

ROWS = 6   # number of rows (row 0 is the top, row ROWS-1 is the bottom)
COLS = 7   # number of columns

EMPTY = 0  # an empty cell
# The four directions used to scan for a line of four, as (drow, dcol):
# horizontal, vertical, and the two diagonals.
DIRECTIONS: Tuple[Tuple[int, int], ...] = ((0, 1), (1, 0), (1, 1), (1, -1))


def in_bounds(row: int, col: int) -> bool:
    """True when (row, col) is a valid cell on the board."""
    return 0 <= row < ROWS and 0 <= col < COLS

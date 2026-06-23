"""Grid dimensions and pure geometry helpers for the Gomoku board.

No game logic lives here: just the constants that describe the 15x15 playfield
and a couple of pure helpers. Mirrors the role of connect_four/board.py and
minesweeper/board.py.
"""
from __future__ import annotations

from typing import Tuple

ROWS = 15  # number of rows (row 0 is the top)
COLS = 15  # number of columns

EMPTY = 0  # an empty intersection
WIN_LENGTH = 5  # how many in a row wins (freestyle; overlines also count)

# The four line orientations used to scan for a run, as (drow, dcol):
# horizontal, vertical, and the two diagonals.
DIRECTIONS: Tuple[Tuple[int, int], ...] = ((0, 1), (1, 0), (1, 1), (1, -1))

Pos = Tuple[int, int]


def in_bounds(row: int, col: int) -> bool:
    """True when (row, col) is a valid cell on the board."""
    return 0 <= row < ROWS and 0 <= col < COLS

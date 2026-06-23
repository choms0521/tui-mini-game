"""Grid dimensions and pure geometry helpers for the Reversi board.

No game logic lives here: just the constants that describe the 8x8 playfield,
the eight scan directions used for outflanking, and a couple of pure helpers.
Mirrors the role of connect_four/board.py.
"""
from __future__ import annotations

from typing import Tuple

SIZE = 8     # the board is SIZE x SIZE

EMPTY = 0    # an empty cell
BLACK = 1    # the human player's discs
WHITE = 2    # the AI player's discs

# A position on the board as (row, col).
Pos = Tuple[int, int]

# The eight directions used to scan for outflanked discs, as (drow, dcol):
# the four orthogonals and the four diagonals.
DIRECTIONS: Tuple[Pos, ...] = (
    (-1, -1), (-1, 0), (-1, 1),
    (0, -1),           (0, 1),
    (1, -1),  (1, 0),  (1, 1),
)


def in_bounds(row: int, col: int) -> bool:
    """True when (row, col) is a valid cell on the board."""
    return 0 <= row < SIZE and 0 <= col < SIZE

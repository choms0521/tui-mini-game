"""Grid dimensions and pure geometry helpers for the Snake board.

No game logic lives here: just the constants that describe the playfield and
helpers that check whether a position is within bounds. Every function is pure
and side-effect free, mirroring the role of tetris/board.py.
"""
from __future__ import annotations

from typing import List, Tuple

WIDTH = 24   # columns of the playfield (not counting the border)
HEIGHT = 16  # rows of the playfield (not counting the border)


def in_bounds(row: int, col: int) -> bool:
    """True when (row, col) is a valid cell inside the playfield."""
    return 0 <= row < HEIGHT and 0 <= col < WIDTH


def all_cells() -> List[Tuple[int, int]]:
    """Return every valid cell in row-major order (deterministic for rng.choice)."""
    return [(r, c) for r in range(HEIGHT) for c in range(WIDTH)]

"""Field dimensions and boundary helpers for Space Invaders.

Provides the width/height constants that every other module imports so the
single source of truth lives here, matching the pattern in tetris/board.py.
"""
from __future__ import annotations

WIDTH = 40    # playfield columns (characters, not pixels)
HEIGHT = 22   # playfield rows: rows 0..20 for aliens/bullets, row 21 for the player

PLAYER_ROW = HEIGHT - 1   # the player always lives on the last row


def in_bounds(row: int, col: int) -> bool:
    """True when (row, col) is inside the playfield."""
    return 0 <= row < HEIGHT and 0 <= col < WIDTH

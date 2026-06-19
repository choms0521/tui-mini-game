"""Tetromino definitions, rotation, and the 7-bag randomizer.

Each shape is a square matrix where ``1`` marks an occupied cell. Keeping the
shapes as immutable tuples lets the rest of the game treat pieces as values.
"""
from __future__ import annotations

import random
from typing import List, Tuple

Matrix = Tuple[Tuple[int, ...], ...]

# Square matrices so a single rotate helper works for every piece.
SHAPES: dict[str, Matrix] = {
    "I": (
        (0, 0, 0, 0),
        (1, 1, 1, 1),
        (0, 0, 0, 0),
        (0, 0, 0, 0),
    ),
    "J": (
        (1, 0, 0),
        (1, 1, 1),
        (0, 0, 0),
    ),
    "L": (
        (0, 0, 1),
        (1, 1, 1),
        (0, 0, 0),
    ),
    "O": (
        (1, 1),
        (1, 1),
    ),
    "S": (
        (0, 1, 1),
        (1, 1, 0),
        (0, 0, 0),
    ),
    "T": (
        (0, 1, 0),
        (1, 1, 1),
        (0, 0, 0),
    ),
    "Z": (
        (1, 1, 0),
        (0, 1, 1),
        (0, 0, 0),
    ),
}

NAMES: Tuple[str, ...] = tuple(SHAPES.keys())


def rotate_cw(matrix: Matrix) -> Matrix:
    """Rotate a square matrix 90 degrees clockwise."""
    return tuple(tuple(row) for row in zip(*matrix[::-1]))


def rotate_ccw(matrix: Matrix) -> Matrix:
    """Rotate a square matrix 90 degrees counter-clockwise."""
    # Three clockwise turns equal one counter-clockwise turn; reuse the helper
    # so there is a single rotation implementation to reason about.
    return rotate_cw(rotate_cw(rotate_cw(matrix)))


def occupied_cells(matrix: Matrix) -> Tuple[Tuple[int, int], ...]:
    """Return the ``(row, col)`` offsets of filled cells within the matrix."""
    return tuple(
        (r, c)
        for r, row in enumerate(matrix)
        for c, value in enumerate(row)
        if value
    )


def fresh_bag(rng: random.Random) -> List[str]:
    """Return a shuffled copy of all seven piece names (a 7-bag)."""
    bag = list(NAMES)
    rng.shuffle(bag)
    return bag

"""Grid geometry and mine layout for Minesweeper.

The board is described purely by a frozenset of mine positions.  All derived
data (adjacent counts, flood-fill reachability) are computed on demand from
that single source of truth so there is nothing mutable to worry about.
"""
from __future__ import annotations

import random
from typing import FrozenSet, Tuple

ROWS = 9
COLS = 9
MINE_COUNT = 10

Pos = Tuple[int, int]


def place_mines(rng: random.Random, rows: int = ROWS, cols: int = COLS,
                count: int = MINE_COUNT) -> FrozenSet[Pos]:
    """Return a frozenset of *count* unique mine positions chosen by *rng*."""
    all_cells: list[Pos] = [(r, c) for r in range(rows) for c in range(cols)]
    chosen = rng.sample(all_cells, count)
    return frozenset(chosen)


def neighbours(pos: Pos, rows: int = ROWS, cols: int = COLS) -> Tuple[Pos, ...]:
    """Return all in-bounds cells adjacent (including diagonals) to *pos*."""
    r, c = pos
    return tuple(
        (r + dr, c + dc)
        for dr in (-1, 0, 1)
        for dc in (-1, 0, 1)
        if (dr, dc) != (0, 0) and 0 <= r + dr < rows and 0 <= c + dc < cols
    )


def adjacent_count(pos: Pos, mines: FrozenSet[Pos], rows: int = ROWS,
                   cols: int = COLS) -> int:
    """Number of mines among the neighbours of *pos*."""
    return sum(1 for n in neighbours(pos, rows, cols) if n in mines)


def flood_reveal(
    start: Pos,
    mines: FrozenSet[Pos],
    already_revealed: FrozenSet[Pos],
    rows: int = ROWS,
    cols: int = COLS,
) -> FrozenSet[Pos]:
    """Return the set of cells that should be newly revealed by opening *start*.

    Performs the classic flood-fill: if *start* has zero adjacent mines it is
    revealed, then its neighbours are visited recursively; the fill stops at
    cells that have one or more adjacent mines (those cells are revealed but do
    not propagate).  If *start* itself is a mine the returned set is empty.
    """
    if start in mines:
        return frozenset()

    revealed: set[Pos] = set()
    frontier: list[Pos] = [start]
    while frontier:
        pos = frontier.pop()
        if pos in revealed or pos in already_revealed:
            continue
        if pos in mines:
            continue
        revealed.add(pos)
        if adjacent_count(pos, mines, rows, cols) == 0:
            frontier.extend(neighbours(pos, rows, cols))

    return frozenset(revealed)

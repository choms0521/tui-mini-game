"""Backtracking Sudoku solver, uniqueness checker, and puzzle generator.

Everything here is pure: randomness is injected via a ``random.Random`` instance
so generation is fully reproducible for a given seed. The solver fills the most
constrained cell first (minimum remaining values) which makes both solving and
uniqueness checking fast enough to run inside the selftest in well under a
second.

This module is the development/verification counterpart to sokoban/solver.py:
it both drives puzzle generation and guards puzzle quality (unique solution).
"""
from __future__ import annotations

import random
from typing import List, Optional, Tuple

import board as B

MutableGrid = List[List[int]]


def _to_mutable(grid: B.Grid) -> MutableGrid:
    """Copy an immutable grid into nested lists for in-place search."""
    return [list(row) for row in grid]


def _to_immutable(grid: MutableGrid) -> B.Grid:
    """Freeze a nested-list grid back into the immutable tuple-of-tuples form."""
    return tuple(tuple(row) for row in grid)


def _candidates(grid: MutableGrid, row: int, col: int) -> List[int]:
    """Return the digits 1-9 that may legally go in an empty (row, col)."""
    used = set()
    for c in range(B.SIZE):
        used.add(grid[row][c])
    for r in range(B.SIZE):
        used.add(grid[r][col])
    br, bc = B.box_origin(row, col)
    for dr in range(B.BOX):
        for dc in range(B.BOX):
            used.add(grid[br + dr][bc + dc])
    return [v for v in range(1, B.SIZE + 1) if v not in used]


def _find_best_cell(grid: MutableGrid) -> Optional[Tuple[int, int, List[int]]]:
    """Return the empty cell with the fewest candidates (MRV heuristic).

    Returns ``None`` when the grid is already full. A cell with one or fewer
    candidates is returned immediately: zero candidates is a dead end the caller
    prunes right away, and a single candidate is a forced move with nothing to
    gain by scanning further. Every other empty cell is compared so the one with
    the fewest candidates wins.
    """
    best: Optional[Tuple[int, int, List[int]]] = None
    for r in range(B.SIZE):
        for c in range(B.SIZE):
            if grid[r][c] != B.EMPTY:
                continue
            cand = _candidates(grid, r, c)
            if len(cand) <= 1:
                return (r, c, cand)
            if best is None or len(cand) < len(best[2]):
                best = (r, c, cand)
    return best


def _fill(grid: MutableGrid, rng: Optional[random.Random]) -> bool:
    """Recursively fill the grid in place. Returns True on success.

    When *rng* is provided the candidate order is shuffled, which is what makes
    a generated full solution look random rather than always the same canonical
    board. Without an rng the first-found candidate order is used.
    """
    target = _find_best_cell(grid)
    if target is None:
        return True  # no empty cells remain — solved
    row, col, candidates = target
    if not candidates:
        return False  # dead end — this branch has no legal digit
    if rng is not None:
        candidates = candidates[:]
        rng.shuffle(candidates)
    for value in candidates:
        grid[row][col] = value
        if _fill(grid, rng):
            return True
        grid[row][col] = B.EMPTY
    return False


def _is_consistent(grid: B.Grid) -> bool:
    """True when *grid* is free of malformed input.

    Every filled cell must hold a digit in ``1..B.SIZE`` and no filled cell may
    duplicate another in its row, column, or box; empty cells are ignored. The
    search only ever writes non-conflicting digits into empty cells, so an
    inconsistent grid (conflicting givens or an out-of-range digit) can never
    become valid. ``solve`` and ``count_solutions`` reject such grids up front so
    their documented "valid solution" / uniqueness contracts stay honest. Note
    the current callers only pass blank or generated-from-valid grids, so this is
    contract hardening rather than a fix for a path the game exercises.
    """
    for row in grid:
        for value in row:
            if value != B.EMPTY and not (1 <= value <= B.SIZE):
                return False
    return not B.conflicts(grid)


def solve(grid: B.Grid, rng: Optional[random.Random] = None) -> Optional[B.Grid]:
    """Return one complete valid solution for *grid*, or None if unsolvable.

    A grid whose filled cells are already inconsistent (a duplicate in some row,
    column, or box, or an out-of-range digit) has no valid completion and yields
    None without searching. Passing an *rng* randomizes the search so a blank
    grid yields a random full board; passing None makes the search deterministic.
    """
    if not _is_consistent(grid):
        return None  # malformed input cannot have a valid solution
    work = _to_mutable(grid)
    if _fill(work, rng):
        return _to_immutable(work)
    return None


def _count_solutions(grid: MutableGrid, limit: int) -> int:
    """Count solutions of *grid* in place, stopping as soon as *limit* is hit.

    Early exit is essential for speed: the uniqueness check only needs to know
    whether a second solution exists, so ``limit=2`` returns the moment a second
    completion is found instead of enumerating the whole solution space.
    """
    target = _find_best_cell(grid)
    if target is None:
        return 1  # a full grid is exactly one solution
    row, col, candidates = target
    if not candidates:
        return 0
    total = 0
    for value in candidates:
        grid[row][col] = value
        total += _count_solutions(grid, limit)
        grid[row][col] = B.EMPTY
        if total >= limit:
            return total  # early exit — no need to keep searching
    return total


def count_solutions(grid: B.Grid, limit: int = 2) -> int:
    """Count solutions of *grid*, capped at *limit* (default 2).

    A return of 1 means the puzzle is proper (exactly one solution); a return of
    2 means "two or more" because the search stops early once the cap is reached.
    A return of 0 means no valid solution exists — including the case of a
    malformed grid (conflicting filled cells or an out-of-range digit), which is
    rejected up front so an already-full but invalid grid is never miscounted
    as the single solution.
    """
    if not _is_consistent(grid):
        return 0  # malformed input has no valid solution
    return _count_solutions(_to_mutable(grid), limit)


def has_unique_solution(grid: B.Grid) -> bool:
    """True when *grid* has exactly one solution."""
    return count_solutions(grid, limit=2) == 1


def generate_full(rng: random.Random) -> B.Grid:
    """Return a complete, valid, randomly filled 9x9 solution grid."""
    blank: B.Grid = tuple(tuple(B.EMPTY for _ in range(B.SIZE)) for _ in range(B.SIZE))
    solution = solve(blank, rng)
    if solution is None:  # pragma: no cover - a blank grid is always solvable
        raise RuntimeError("failed to generate a full Sudoku solution")
    return solution


def generate_puzzle(
    rng: random.Random,
    givens: int = 32,
) -> Tuple[B.Grid, B.Grid]:
    """Generate a puzzle with a unique solution and its full solution.

    *givens* is the target number of filled cells (difficulty: fewer givens is
    harder). It is clamped to the range ``[B.SIZE, B.SIZE * B.SIZE]`` (9..81), so
    a request outside that range is pulled to the nearest bound. Cells are
    removed in a random order; a removal is kept only when the puzzle still has
    exactly one solution, so the returned puzzle is always proper. The target is
    a goal, not a guarantee — the uniqueness check (not the clamp) is what
    ultimately bounds how few givens remain, since removal stops early once no
    further cell can be cleared without introducing a second solution.

    Returns ``(puzzle, solution)`` as immutable grids.
    """
    target = max(B.SIZE, min(B.SIZE * B.SIZE, givens))
    solution = generate_full(rng)
    puzzle = _to_mutable(solution)

    cells = B.all_cells()
    rng.shuffle(cells)
    filled = B.SIZE * B.SIZE
    for (r, c) in cells:
        if filled <= target:
            break
        saved = puzzle[r][c]
        puzzle[r][c] = B.EMPTY
        if has_unique_solution(_to_immutable(puzzle)):
            filled -= 1
        else:
            puzzle[r][c] = saved  # removal broke uniqueness — put it back
    return _to_immutable(puzzle), solution


if __name__ == "__main__":
    demo_rng = random.Random(0)
    demo_puzzle, demo_solution = generate_puzzle(demo_rng, givens=32)
    given_count = sum(1 for row in demo_puzzle for v in row if v != B.EMPTY)
    unique = has_unique_solution(demo_puzzle)
    print(f"Generated puzzle with {given_count} givens; unique={unique}")

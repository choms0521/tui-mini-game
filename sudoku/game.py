"""Immutable game state and the transitions that drive a game of Sudoku.

Every transition takes a :class:`GameState` and returns a new one via
``dataclasses.replace``; nothing is mutated in place, so the game loop can
compare object identity to detect real changes. Randomness (puzzle generation)
is injected via a ``random.Random`` instance, keeping the logic pure and the
selftest fully deterministic. This module never imports blessed.
"""
from __future__ import annotations

import random
from dataclasses import dataclass, replace
from typing import Tuple

import board as B
import solver as S

# Default difficulty: number of givens left in a freshly generated puzzle.
# Fewer givens is harder; this is a comfortable medium.
DEFAULT_GIVENS = 32

Cell = Tuple[int, int]


@dataclass(frozen=True)
class GameState:
    """Complete, immutable snapshot of one Sudoku game.

    givens   -- the fixed puzzle cells (0 = blank); these can never be edited.
    grid     -- the current board including the player's entries.
    solution -- the unique completed solution for this puzzle.
    cursor   -- (row, col) of the highlighted cell.
    won      -- True once ``grid`` equals ``solution``.
    """

    givens: B.Grid
    grid: B.Grid
    solution: B.Grid
    cursor: Cell = (0, 0)
    won: bool = False


def new_game(rng: random.Random, givens: int = DEFAULT_GIVENS) -> GameState:
    """Create a fresh game with a newly generated, uniquely solvable puzzle."""
    puzzle, solution = S.generate_puzzle(rng, givens=givens)
    return GameState(
        givens=puzzle,
        grid=puzzle,
        solution=solution,
        cursor=(0, 0),
        won=False,
    )


def is_given(state: GameState, row: int, col: int) -> bool:
    """True when (row, col) is a fixed puzzle cell the player cannot change."""
    return state.givens[row][col] != B.EMPTY


def move_cursor(state: GameState, dr: int, dc: int) -> GameState:
    """Move the cursor by (dr, dc), clamped to the grid bounds.

    Returns the same state object when the move would not change the cursor, so
    the game loop can skip a redraw (mirrors minesweeper.move_cursor).
    """
    r, c = state.cursor
    new_r = max(0, min(B.SIZE - 1, r + dr))
    new_c = max(0, min(B.SIZE - 1, c + dc))
    if (new_r, new_c) == state.cursor:
        return state
    return replace(state, cursor=(new_r, new_c))


def _with_value(state: GameState, row: int, col: int, value: int) -> GameState:
    """Return a new state with (row, col) set to *value*, recomputing ``won``."""
    new_row = state.grid[row][:col] + (value,) + state.grid[row][col + 1:]
    new_grid = state.grid[:row] + (new_row,) + state.grid[row + 1:]
    won = new_grid == state.solution
    return replace(state, grid=new_grid, won=won)


def set_value(state: GameState, value: int) -> GameState:
    """Place *value* (1-9) in the cell under the cursor.

    Given cells are protected; setting a value once the puzzle is won, or
    setting the value already present, returns the same state object so no
    needless redraw happens.
    """
    if state.won:
        return state
    r, c = state.cursor
    if is_given(state, r, c):
        return state
    if not (1 <= value <= B.SIZE):
        return state
    if state.grid[r][c] == value:
        return state
    return _with_value(state, r, c, value)


def clear_value(state: GameState) -> GameState:
    """Clear the cell under the cursor (set it back to empty).

    Given cells are protected and already-empty cells return the same state
    object so the game loop can skip a redraw.
    """
    if state.won:
        return state
    r, c = state.cursor
    if is_given(state, r, c):
        return state
    if state.grid[r][c] == B.EMPTY:
        return state
    return _with_value(state, r, c, B.EMPTY)


def restart(rng: random.Random, _state: GameState, givens: int = DEFAULT_GIVENS) -> GameState:
    """Start a brand new puzzle (used for the 'r' / new-puzzle action).

    The current state is accepted so this matches the ``restart(rng, state)``
    call convention shared with the other games, but it is intentionally unused:
    a restart always builds a fresh puzzle from scratch, with difficulty set by
    *givens*.
    """
    return new_game(rng, givens=givens)

"""Immutable game state and the transitions that drive a game of Tetris.

Every transition takes a :class:`GameState` and returns a new one, so the game
loop can compare object identity to tell whether anything actually changed.
Randomness lives outside the state: spawning transitions receive a
``random.Random`` so the state itself stays a pure value.
"""
from __future__ import annotations

import random
from dataclasses import dataclass, replace
from typing import Tuple

import board as B
import pieces as P

# Points awarded for clearing 0..4 lines at once, multiplied by the level.
SCORE_TABLE = {0: 0, 1: 100, 2: 300, 3: 500, 4: 800}

# Horizontal offsets attempted when a rotation is blocked (basic wall kick).
_KICKS: Tuple[int, ...] = (0, -1, 1, -2, 2)


@dataclass(frozen=True)
class Active:
    """The falling piece: its shape matrix and its top-left position."""

    name: str
    matrix: P.Matrix
    row: int
    col: int

    def cells(self) -> Tuple[Tuple[int, int], ...]:
        """Absolute ``(row, col)`` board coordinates the piece occupies."""
        return tuple(
            (self.row + r, self.col + c) for r, c in P.occupied_cells(self.matrix)
        )


@dataclass(frozen=True)
class GameState:
    grid: B.Grid
    active: Active
    bag: Tuple[str, ...]
    score: int = 0
    lines: int = 0
    level: int = 1
    game_over: bool = False


def _spawn(name: str) -> Active:
    """Create a piece centred at the top of the board."""
    matrix = P.SHAPES[name]
    col = (B.WIDTH - len(matrix[0])) // 2
    return Active(name=name, matrix=matrix, row=0, col=col)


def _ensure_bag(bag: Tuple[str, ...], rng: random.Random) -> Tuple[str, ...]:
    """Guarantee the bag has at least one piece by refilling when empty."""
    return bag if bag else tuple(P.fresh_bag(rng))


def new_game(rng: random.Random) -> GameState:
    """Start a fresh game with a centred first piece."""
    bag = _ensure_bag((), rng)
    first, bag = bag[0], bag[1:]
    bag = _ensure_bag(bag, rng)
    return GameState(grid=B.empty_grid(), active=_spawn(first), bag=bag)


def next_name(state: GameState) -> str:
    """Name of the upcoming piece (for the preview panel)."""
    return state.bag[0] if state.bag else P.NAMES[0]


def _lock(state: GameState, rng: random.Random) -> GameState:
    """Freeze the active piece, clear lines, score, and spawn the next piece."""
    grid = B.place(state.grid, state.active.cells(), state.active.name)
    grid, cleared = B.clear_lines(grid)
    lines = state.lines + cleared
    # Normal play clears at most 4 rows; cap defensively so an unusual board
    # state can never raise a KeyError.
    score = state.score + SCORE_TABLE.get(min(cleared, 4), 0) * state.level
    level = 1 + lines // 10

    bag = _ensure_bag(state.bag, rng)
    name, bag = bag[0], bag[1:]
    bag = _ensure_bag(bag, rng)
    active = _spawn(name)
    game_over = not B.fits(grid, active.cells())

    return replace(
        state,
        grid=grid,
        active=active,
        bag=bag,
        score=score,
        lines=lines,
        level=level,
        game_over=game_over,
    )


def try_move(state: GameState, drow: int, dcol: int) -> GameState:
    """Shift the piece; return the unchanged state if blocked."""
    if state.game_over:
        return state
    moved = replace(state.active, row=state.active.row + drow, col=state.active.col + dcol)
    if B.fits(state.grid, moved.cells()):
        return replace(state, active=moved)
    return state


def try_rotate(state: GameState, clockwise: bool = True) -> GameState:
    """Rotate the piece with a basic wall kick; unchanged if nothing fits."""
    if state.game_over:
        return state
    matrix = (
        P.rotate_cw(state.active.matrix)
        if clockwise
        else P.rotate_ccw(state.active.matrix)
    )
    for dc in _KICKS:
        candidate = replace(state.active, matrix=matrix, col=state.active.col + dc)
        if B.fits(state.grid, candidate.cells()):
            return replace(state, active=candidate)
    return state


def step_down(state: GameState, rng: random.Random) -> GameState:
    """Apply one step of gravity, locking the piece if it cannot fall."""
    if state.game_over:
        return state
    moved = replace(state.active, row=state.active.row + 1)
    if B.fits(state.grid, moved.cells()):
        return replace(state, active=moved)
    return _lock(state, rng)


def hard_drop(state: GameState, rng: random.Random) -> GameState:
    """Drop the piece straight down and lock it immediately."""
    if state.game_over:
        return state
    active = state.active
    distance = 0
    while True:
        moved = replace(active, row=active.row + 1)
        if B.fits(state.grid, moved.cells()):
            active = moved
            distance += 1
        else:
            break
    state = replace(state, active=active, score=state.score + distance * 2)
    return _lock(state, rng)


def ghost_cells(state: GameState) -> Tuple[Tuple[int, int], ...]:
    """Where the active piece would land if dropped (for the ghost preview)."""
    active = state.active
    while True:
        moved = replace(active, row=active.row + 1)
        if B.fits(state.grid, moved.cells()):
            active = moved
        else:
            break
    return active.cells()

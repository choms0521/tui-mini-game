"""Immutable game state and pure transitions for 2048.

Every transition takes a :class:`GameState` and returns a new one.  Randomness
is injected via a ``random.Random`` instance so state stays a pure value and
the selftest remains deterministic.
"""
from __future__ import annotations

import random
from dataclasses import dataclass, replace
from typing import Literal

import board as B

Direction = Literal["left", "right", "up", "down"]

_SLIDE = {
    "left":  B.slide_left,
    "right": B.slide_right,
    "up":    B.slide_up,
    "down":  B.slide_down,
}


@dataclass(frozen=True)
class GameState:
    """Complete, immutable snapshot of a 2048 game."""

    grid: B.Grid
    score: int = 0
    won: bool = False
    game_over: bool = False


def new_game(rng: random.Random) -> GameState:
    """Start a fresh game with two tiles already on the board."""
    grid = B.empty_grid()
    grid = B.spawn_tile(grid, rng)
    grid = B.spawn_tile(grid, rng)
    return GameState(grid=grid)


def move(state: GameState, direction: Direction, rng: random.Random) -> GameState:
    """Apply a slide in *direction* and return the resulting state.

    If the slide does not change the grid no tile is spawned and the *same*
    state object is returned (identity preserved), so the main loop can use
    ``new_state is not state`` to detect a no-op — exactly like tetris.
    """
    if state.game_over:
        return state

    slide_fn = _SLIDE[direction]
    new_grid, gained = slide_fn(state.grid)

    # No change → return the original object so callers can use identity check.
    if new_grid == state.grid:
        return state

    # Spawn only after a real change.
    empties = B.empty_cells(new_grid)
    if empties:
        new_grid = B.spawn_tile(new_grid, rng)

    new_score = state.score + gained
    # won is sticky: once the 2048 tile appears it stays true.
    new_won = state.won or B.has_won(new_grid)
    new_game_over = B.is_stuck(new_grid)

    return replace(
        state,
        grid=new_grid,
        score=new_score,
        won=new_won,
        game_over=new_game_over,
    )

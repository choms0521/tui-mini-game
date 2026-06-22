"""Immutable game state and all transitions for Minesweeper.

Every function takes a :class:`GameState` and returns a new one; nothing is
mutated in place.  Randomness is injected via a ``random.Random`` instance so
the game logic is deterministic given the same seed.
"""
from __future__ import annotations

import random
from dataclasses import dataclass
from dataclasses import replace
from typing import FrozenSet, Tuple

import board as B


@dataclass(frozen=True)
class GameState:
    """Complete, immutable snapshot of a Minesweeper game."""

    mines: FrozenSet[B.Pos]
    revealed: FrozenSet[B.Pos]
    flagged: FrozenSet[B.Pos]
    cursor: B.Pos
    game_over: bool
    won: bool
    rows: int = B.ROWS
    cols: int = B.COLS


def new_game(rng: random.Random, rows: int = B.ROWS, cols: int = B.COLS,
             mine_count: int = B.MINE_COUNT) -> GameState:
    """Return a freshly started game with mines placed by *rng*."""
    mines = B.place_mines(rng, rows, cols, mine_count)
    return GameState(
        mines=mines,
        revealed=frozenset(),
        flagged=frozenset(),
        cursor=(0, 0),
        game_over=False,
        won=False,
        rows=rows,
        cols=cols,
    )


def move_cursor(state: GameState, dr: int, dc: int) -> GameState:
    """Move the cursor by (dr, dc), clamped to the grid bounds."""
    if state.game_over or state.won:
        return state
    r, c = state.cursor
    new_r = max(0, min(state.rows - 1, r + dr))
    new_c = max(0, min(state.cols - 1, c + dc))
    if (new_r, new_c) == state.cursor:
        return state
    return replace(state, cursor=(new_r, new_c))


def reveal(state: GameState) -> GameState:
    """Reveal the cell under the cursor.

    - Flagged cells are not revealed (the player must remove the flag first).
    - Revealing a mine ends the game.
    - Revealing a zero-count cell flood-fills the connected zero region.
    - Revealing the last safe cell wins the game.
    """
    if state.game_over or state.won:
        return state

    pos = state.cursor
    if pos in state.flagged or pos in state.revealed:
        return state

    if pos in state.mines:
        # Reveal all mines on loss.
        return replace(state, revealed=state.revealed | state.mines, game_over=True)

    newly = B.flood_reveal(pos, state.mines, state.revealed, state.rows, state.cols)
    new_revealed = state.revealed | newly

    safe_count = state.rows * state.cols - len(state.mines)
    won = len(new_revealed - state.mines) == safe_count

    return replace(state, revealed=new_revealed, won=won)


def toggle_flag(state: GameState) -> GameState:
    """Toggle a flag on the cell under the cursor.

    Already-revealed cells cannot be flagged.
    """
    if state.game_over or state.won:
        return state

    pos = state.cursor
    if pos in state.revealed:
        return state

    if pos in state.flagged:
        return replace(state, flagged=state.flagged - {pos})
    return replace(state, flagged=state.flagged | {pos})


def restart(rng: random.Random, state: GameState) -> GameState:
    """Start a fresh game with the same grid dimensions."""
    return new_game(rng, state.rows, state.cols,
                    len(state.mines) if state.mines else B.MINE_COUNT)

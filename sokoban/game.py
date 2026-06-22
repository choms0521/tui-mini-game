"""Immutable game state and the transitions that drive a game of Sokoban.

Every transition takes a :class:`SokobanState` and returns a new one (or the
same object on a no-op), so the game loop can compare object identity to tell
whether anything actually changed.  History is stored as a tuple of lightweight
``(player, boxes)`` snapshots so undo never nests full states inside each other.
"""
from __future__ import annotations

import random
from dataclasses import dataclass, replace
from typing import FrozenSet, Tuple

import levels as L

# Direction vectors: (delta_row, delta_col)
DIRECTIONS = {
    "up":    (-1, 0),
    "down":  (1, 0),
    "left":  (0, -1),
    "right": (0, 1),
}

# A lightweight snapshot saved before each move so undo can step back.
_Snapshot = Tuple[Tuple[int, int], FrozenSet[Tuple[int, int]]]


@dataclass(frozen=True)
class SokobanState:
    """Complete game state for one level.

    Static per-level data (walls, goals, width, height) does not change after
    a level is loaded.  Dynamic data (player, boxes, moves, history) changes
    with each player action.  All fields are immutable; transitions return a
    new state via :func:`dataclasses.replace`.
    """

    # --- static (per level) ---
    walls: FrozenSet[Tuple[int, int]]
    goals: FrozenSet[Tuple[int, int]]
    level_width: int
    level_height: int
    level_index: int

    # --- dynamic ---
    player: Tuple[int, int]
    boxes: FrozenSet[Tuple[int, int]]
    moves: int

    # --- control flags ---
    solved: bool   # True when every box sits on a goal
    won: bool      # True after completing the last level

    # --- undo stack: tuple of (player, boxes) snapshots ---
    history: Tuple[_Snapshot, ...]


def _check_solved(
    boxes: FrozenSet[Tuple[int, int]],
    goals: FrozenSet[Tuple[int, int]],
) -> bool:
    """True when every goal has a box on it."""
    return boxes >= goals


def new_game(rng: random.Random | None = None, level_index: int = 0) -> SokobanState:
    """Start a fresh game at the given level.

    *rng* is accepted for interface consistency with the other games; it is not
    used because Sokoban levels are deterministic.
    """
    walls, goals, boxes, player, width, height = L.parse_level(level_index)
    return SokobanState(
        walls=walls,
        goals=goals,
        level_width=width,
        level_height=height,
        level_index=level_index,
        player=player,
        boxes=boxes,
        moves=0,
        solved=_check_solved(boxes, goals),
        won=False,
        history=(),
    )


def move(state: SokobanState, direction: str) -> SokobanState:
    """Attempt to move the player one tile in *direction*.

    Rules
    -----
    - Walking into a wall: no-op, return the *same* state object.
    - Pushing a box: allowed only when the tile beyond the box is empty floor
      or a goal square (not a wall and not a second box).
    - On a no-op the state object is returned unchanged (``is`` comparison).
    - On success a snapshot of (player, boxes) is prepended to ``history``
      before the move is applied, so undo can restore it.
    """
    if state.solved or state.won:
        return state

    dr, dc = DIRECTIONS[direction]
    pr, pc = state.player
    nr, nc = pr + dr, pc + dc

    # Moving into a wall: no-op.
    if (nr, nc) in state.walls:
        return state

    if (nr, nc) in state.boxes:
        # Attempted push: tile beyond the box must be empty floor or a goal.
        br, bc = nr + dr, nc + dc
        if (br, bc) in state.walls or (br, bc) in state.boxes:
            return state  # blocked by wall or second box — no-op
        # Valid push: update boxes.
        new_boxes = (state.boxes - {(nr, nc)}) | {(br, bc)}
    else:
        new_boxes = state.boxes

    # Save snapshot before applying the move.
    snapshot: _Snapshot = (state.player, state.boxes)
    new_history = (snapshot,) + state.history

    solved = _check_solved(new_boxes, state.goals)

    return replace(
        state,
        player=(nr, nc),
        boxes=frozenset(new_boxes),
        moves=state.moves + 1,
        solved=solved,
        history=new_history,
    )


def undo(state: SokobanState) -> SokobanState:
    """Restore the position before the last move.

    If there is no history, return the same state object unchanged.
    """
    if not state.history:
        return state

    prev_player, prev_boxes = state.history[0]
    remaining_history = state.history[1:]
    solved = _check_solved(prev_boxes, state.goals)

    return replace(
        state,
        player=prev_player,
        boxes=prev_boxes,
        moves=max(0, state.moves - 1),
        solved=solved,
        history=remaining_history,
    )


def restart_level(state: SokobanState) -> SokobanState:
    """Restart the current level from scratch."""
    return new_game(level_index=state.level_index)


def advance_level(state: SokobanState) -> SokobanState:
    """Move to the next level, or mark the game as won on the last level."""
    next_index = state.level_index + 1
    if next_index >= len(L.LEVELS):
        return replace(state, won=True)
    return new_game(level_index=next_index)


def level_count() -> int:
    """Total number of available levels."""
    return len(L.LEVELS)

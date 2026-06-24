"""Immutable game state and pure transition functions for Frogger.

No blessed imports here. All game logic is side-effect-free so it can be
tested headlessly. Randomness is not needed: obstacle positions are
deterministic from lane pattern + offset.
"""
from __future__ import annotations

from dataclasses import dataclass, replace
from typing import FrozenSet, Tuple

import board as B

# Type alias for a (row, col) position.
Pos = Tuple[int, int]


@dataclass(frozen=True)
class GameState:
    """Complete, immutable snapshot of one Frogger game."""

    frog: Pos                      # (row, col) current frog position
    lanes: Tuple[B.LaneDef, ...]   # static lane definitions (same every game)
    offsets: Tuple[int, ...]       # per-lane scroll accumulator (len == len(lanes))
    lives: int
    score: int
    filled_goals: FrozenSet[int]   # indices into B.GOAL_COLS that are filled
    tick: int
    game_over: bool
    won: bool


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------

def new_game() -> GameState:
    """Return a fresh game with full lives, zero score, and frog at the start."""
    return GameState(
        frog=(B.START_ROW, B.START_COL),
        lanes=B.LANES,
        offsets=tuple(0 for _ in B.LANES),
        lives=B.INITIAL_LIVES,
        score=0,
        filled_goals=frozenset(),
        tick=0,
        game_over=False,
        won=False,
    )


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _reset_frog(state: GameState) -> GameState:
    """Return state with frog back at the start position."""
    return replace(state, frog=(B.START_ROW, B.START_COL))


def _lose_life(state: GameState) -> GameState:
    """Deduct one life and reset the frog; set game_over when lives reach 0."""
    new_lives = state.lives - 1
    if new_lives <= 0:
        return replace(state, lives=0, game_over=True, frog=(B.START_ROW, B.START_COL))
    s = replace(state, lives=new_lives)
    return _reset_frog(s)


# ---------------------------------------------------------------------------
# Move frog
# ---------------------------------------------------------------------------

def move_frog(state: GameState, drow: int, dcol: int) -> GameState:
    """Move the frog by (drow, dcol), clamped to field bounds.

    When the frog reaches the goal row (row 0):
    - Landing on an empty goal slot: score, fill slot, reset frog, check win.
    - Landing on a filled slot or non-slot column: treated as a wall (no-op).
    """
    if state.game_over or state.won:
        return state

    frow, fcol = state.frog
    new_row = max(0, min(B.HEIGHT - 1, frow + drow))
    new_col = max(0, min(B.WIDTH - 1, fcol + dcol))

    # Check goal-row landing.
    if new_row == B.GOAL_ROW:
        # Find which goal slot (if any) the frog lands on.
        slot_idx: int | None = None
        for i, gc in enumerate(B.GOAL_COLS):
            if new_col == gc:
                slot_idx = i
                break

        if slot_idx is None:
            # Not a valid goal slot column — treat as a wall (no movement).
            return state

        if slot_idx in state.filled_goals:
            # Already-filled slot — no-op.
            return state

        # Land in empty slot: score, fill, reset frog.
        new_filled = state.filled_goals | {slot_idx}
        new_score = state.score + B.SCORE_PER_GOAL
        won = len(new_filled) == B.NUM_GOALS
        s = replace(
            state,
            score=new_score,
            filled_goals=frozenset(new_filled),
            won=won,
        )
        return _reset_frog(s)

    return replace(state, frog=(new_row, new_col))


# ---------------------------------------------------------------------------
# Tick
# ---------------------------------------------------------------------------

def tick(state: GameState) -> GameState:
    """Advance one game tick.

    Order of operations:
    1. Advance every lane's offset by direction * speed (wrapping) and
       increment the tick counter (a tick always counts, even when the frog
       dies during this tick).
    2. If frog is on a river lane, carry it by that lane's direction * speed.
    3. If frog carried off-field edge -> lose a life.
    4. Resolve road collisions and river drowning at the frog's current row.
    """
    if state.game_over or state.won:
        return state

    # Step 1: advance offsets.
    new_offsets = tuple(
        (state.offsets[i] + lane.direction * lane.speed) % B.WIDTH
        if lane.direction != 0 else 0
        for i, lane in enumerate(state.lanes)
    )
    s = replace(state, offsets=new_offsets, tick=state.tick + 1)

    # Step 2: carry frog if on a river lane.
    frow, fcol = s.frog
    lane = s.lanes[frow]

    if lane.kind == "river":
        carried_col = fcol + lane.direction * lane.speed
        # Step 3: off-field edge -> lose a life.
        if carried_col < 0 or carried_col >= B.WIDTH:
            return _lose_life(s)
        s = replace(s, frog=(frow, carried_col))
        frow, fcol = s.frog

    # Step 4: collision / drowning resolution.
    s = _resolve_lane(s)
    return s


def _resolve_lane(state: GameState) -> GameState:
    """Check the frog's current lane for collisions or drowning."""
    frow, fcol = state.frog

    # Goal row: safe (frog resets to start after scoring; no collision here).
    if frow == B.GOAL_ROW:
        return state

    lane = state.lanes[frow]
    offset = state.offsets[frow]
    obs = B.obstacle_cells(lane, offset)

    if lane.kind == "road":
        # Frog sharing a cell with a car -> die.
        if fcol in obs:
            return _lose_life(state)

    elif lane.kind == "river":
        # Frog must be ON a log to survive; not on log -> drown.
        if fcol not in obs:
            return _lose_life(state)

    # "safe" lanes: always fine.
    return state

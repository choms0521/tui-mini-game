"""Immutable game state and the transitions that drive a game of Snake.

Every transition takes a GameState and returns a new one via dataclasses.replace,
so the game loop can compare object identity to detect actual changes.
Randomness is injected via a random.Random instance so state transitions are
pure and the selftest is fully deterministic.
"""
from __future__ import annotations

import random
from dataclasses import dataclass, replace
from typing import Optional, Tuple

import board as B

# Direction constants as (drow, dcol) tuples.
UP    = (-1,  0)
DOWN  = ( 1,  0)
LEFT  = ( 0, -1)
RIGHT = ( 0,  1)

# Tick speed: BASE_TICK seconds per move at score 0; shortens as score grows.
BASE_TICK = 0.35
MIN_TICK  = 0.08
SCORE_STEP = 0.001   # each point shaves this many seconds off the interval

Cell = Tuple[int, int]
Direction = Tuple[int, int]


def tick_interval(score: int) -> float:
    """Seconds between snake advances for the given score."""
    return max(MIN_TICK, BASE_TICK - score * SCORE_STEP)


@dataclass(frozen=True)
class GameState:
    """Complete, immutable snapshot of one Snake game.

    body   -- tuple of (row, col) with the head at index 0.
    direction -- current movement direction as (drow, dcol).
    food  -- (row, col) of the current food cell.
    score  -- points accumulated so far.
    game_over -- True once the snake has collided with a wall or itself.
    """

    body: Tuple[Cell, ...]
    direction: Direction
    food: Cell
    score: int = 0
    game_over: bool = False


def _spawn_food(body: Tuple[Cell, ...], rng: random.Random) -> Cell:
    """Return a random empty cell for the new food, using a sorted candidate list
    to guarantee reproducible results across Python versions."""
    occupied = set(body)
    candidates = [cell for cell in B.all_cells() if cell not in occupied]
    if not candidates:
        # Board is entirely full (extremely unlikely in normal play).
        return body[-1]  # fallback: overlap with tail, harmless edge case
    return rng.choice(candidates)


def new_game(rng: random.Random) -> GameState:
    """Create a fresh game with the snake centred and heading right."""
    start_row = B.HEIGHT // 2
    start_col = B.WIDTH // 2
    body: Tuple[Cell, ...] = (
        (start_row, start_col),
        (start_row, start_col - 1),
        (start_row, start_col - 2),
    )
    food = _spawn_food(body, rng)
    return GameState(body=body, direction=RIGHT, food=food)


def turn(state: GameState, new_dir: Direction) -> GameState:
    """Request a direction change; ignores direct reversals (180-degree turns).

    Returns the same state object if the turn is illegal (mirrors tetris
    try_move returning state unchanged when blocked).
    """
    if state.game_over:
        return state
    dr, dc = state.direction
    # Prevent reversing directly into the snake's own neck.
    if new_dir == (-dr, -dc):
        return state
    return replace(state, direction=new_dir)


def advance(state: GameState, rng: random.Random) -> GameState:
    """Move the snake one step in its current direction.

    Handles: wall collision (game over), self-collision (game over),
    eating food (grow + new food + score), and normal movement.
    """
    if state.game_over:
        return state

    head_r, head_c = state.body[0]
    dr, dc = state.direction
    new_head: Cell = (head_r + dr, head_c + dc)

    # Wall collision.
    if not B.in_bounds(new_head[0], new_head[1]):
        return replace(state, game_over=True)

    ate_food = new_head == state.food

    if ate_food:
        # Grow: prepend new head, keep entire old body.
        new_body = (new_head,) + state.body
        new_score = state.score + 1
        new_food = _spawn_food(new_body, rng)
    else:
        # Move: prepend new head, drop the tail.
        new_body = (new_head,) + state.body[:-1]
        new_score = state.score
        new_food = state.food

    # Self-collision: head must not overlap with the body cells that remain
    # after movement. When not growing, the tail has already vacated, so we
    # check against new_body[1:] (all cells except the new head itself).
    if new_head in set(new_body[1:]):
        return replace(state, game_over=True)

    return replace(
        state,
        body=new_body,
        food=new_food,
        score=new_score,
    )

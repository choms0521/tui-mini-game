"""Immutable game state and the transitions that drive a game of Space Invaders.

Every transition takes a GameState and returns a new one (or the same object
on a no-op), so the game loop can compare identity to detect changes.
Randomness is injected via a random.Random instance so state stays a pure value.
"""
from __future__ import annotations

import random
from dataclasses import dataclass, replace
from typing import Tuple

import board as B

# Fleet layout: rows x cols of aliens, placed near the top of the field.
FLEET_ROWS = 4
FLEET_COLS = 10
FLEET_TOP = 1          # row where the topmost alien row starts
FLEET_COL_START = 5    # leftmost column of the initial fleet

# Points per alien killed.
SCORE_PER_KILL = 10

# Maximum live bullets the player can have in flight at once.
MAX_BULLETS = 3

# Type aliases for positions.
Pos = Tuple[int, int]


@dataclass(frozen=True)
class GameState:
    """Complete, immutable snapshot of one Space Invaders game."""

    player_col: int
    bullets: Tuple[Pos, ...]       # each bullet is (row, col); row decreases each tick
    aliens: Tuple[Pos, ...]        # (row, col) for every living alien
    direction: int                 # +1 = moving right, -1 = moving left
    score: int = 0
    game_over: bool = False
    won: bool = False


def _build_fleet() -> Tuple[Pos, ...]:
    """Return starting positions for the full alien fleet."""
    positions = []
    for r in range(FLEET_ROWS):
        for c in range(FLEET_COLS):
            positions.append((FLEET_TOP + r, FLEET_COL_START + c * 2))
    return tuple(positions)


def new_game(rng: random.Random) -> GameState:  # noqa: ARG001  (rng reserved for future use)
    """Start a fresh game with a centred player ship and full alien fleet."""
    player_col = B.WIDTH // 2
    return GameState(
        player_col=player_col,
        bullets=(),
        aliens=_build_fleet(),
        direction=1,
    )


# ---------------------------------------------------------------------------
# Player actions
# ---------------------------------------------------------------------------

def move_player(state: GameState, dcol: int) -> GameState:
    """Move the player left (-1) or right (+1), clamped to field bounds.

    Returns the same object when the player is already at the edge so the
    game loop's identity check (`new_state is not state`) stays correct.
    """
    if state.game_over or state.won:
        return state
    new_col = state.player_col + dcol
    # Clamp to field; return the same object if nothing moved.
    new_col = max(0, min(B.WIDTH - 1, new_col))
    if new_col == state.player_col:
        return state
    return replace(state, player_col=new_col)


def fire(state: GameState) -> GameState:
    """Add a bullet just above the player ship, respecting the bullet cap.

    Returns the same object when at the cap so identity checks work.
    """
    if state.game_over or state.won:
        return state
    if len(state.bullets) >= MAX_BULLETS:
        return state
    bullet: Pos = (B.PLAYER_ROW - 1, state.player_col)
    return replace(state, bullets=state.bullets + (bullet,))


# ---------------------------------------------------------------------------
# Tick transitions
# ---------------------------------------------------------------------------

def advance_bullets(state: GameState) -> GameState:
    """Move every bullet one row upward, remove out-of-field bullets, then
    resolve bullet-alien collisions."""
    if state.game_over or state.won:
        return state

    # Move bullets upward (decreasing row).
    moved: Tuple[Pos, ...] = tuple(
        (r - 1, c) for r, c in state.bullets if r - 1 >= 0
    )
    new_state = replace(state, bullets=moved)
    return _resolve_collisions(new_state)


def advance_fleet(state: GameState) -> GameState:
    """Move the alien fleet one step, handle edge bounces, check for loss."""
    if state.game_over or state.won:
        return state

    aliens = state.aliens
    direction = state.direction

    # Check whether a horizontal shift by `direction` would push any alien
    # out of the playfield bounds.
    cols = [c for _, c in aliens]
    if direction == 1:
        edge_col = max(cols) if cols else 0
    else:
        edge_col = min(cols) if cols else 0

    if (direction == 1 and edge_col + 1 >= B.WIDTH) or (
        direction == -1 and edge_col - 1 < 0
    ):
        # Step every alien down one row; flip direction; do NOT shift sideways.
        new_aliens: Tuple[Pos, ...] = tuple((r + 1, c) for r, c in aliens)
        new_direction = -direction
    else:
        # Shift entire fleet horizontally.
        new_aliens = tuple((r, c + direction) for r, c in aliens)
        new_direction = direction

    new_state = replace(state, aliens=new_aliens, direction=new_direction)
    new_state = _resolve_collisions(new_state)

    # Lose if any alien has reached or passed the player row.
    if not new_state.game_over and not new_state.won:
        if any(r >= B.PLAYER_ROW for r, _ in new_state.aliens):
            new_state = replace(new_state, game_over=True)

    return new_state


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _resolve_collisions(state: GameState) -> GameState:
    """Remove any bullet-alien pair that occupies the same cell; award score.

    Sets `won=True` when the last alien is destroyed.
    """
    bullet_set = set(state.bullets)
    alien_set = set(state.aliens)

    hit_aliens = alien_set & bullet_set
    if not hit_aliens:
        return state

    surviving_aliens: Tuple[Pos, ...] = tuple(a for a in state.aliens if a not in hit_aliens)
    surviving_bullets: Tuple[Pos, ...] = tuple(b for b in state.bullets if b not in hit_aliens)
    new_score = state.score + len(hit_aliens) * SCORE_PER_KILL
    won = len(surviving_aliens) == 0

    return replace(
        state,
        bullets=surviving_bullets,
        aliens=surviving_aliens,
        score=new_score,
        won=won,
    )

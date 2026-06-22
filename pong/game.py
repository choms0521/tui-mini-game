"""Immutable Pong state and the transitions that drive it.

Every transition returns a new :class:`GameState` via ``dataclasses.replace``
— nothing is mutated in place. Randomness is injected via a ``random.Random``
instance so the self-test can drive the game deterministically.
"""
from __future__ import annotations

import random
from dataclasses import dataclass, replace
from typing import Literal

import config as C


@dataclass(frozen=True)
class GameState:
    ball_x: int          # horizontal position inside the court (0 .. PLAY_W-1)
    ball_y: int          # vertical position inside the court (0 .. PLAY_H-1)
    ball_vx: int         # horizontal velocity: +1 right, -1 left
    ball_vy: int         # vertical velocity: +1 down, -1 up
    left_y: int          # top row of the left paddle
    right_y: int         # top row of the right paddle
    left_score: int = 0
    right_score: int = 0
    game_over: bool = False
    winner: str = ""     # "Player" or "CPU" when game_over is True
    started: bool = False  # False until space is pressed the first time
    paused: bool = False


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _clamp_paddle(y: int) -> int:
    """Keep the paddle top row so the whole paddle fits inside the court."""
    return max(0, min(C.PLAY_H - C.PADDLE_H, y))


def _center_y() -> int:
    """Vertical center for a paddle start position."""
    return (C.PLAY_H - C.PADDLE_H) // 2


def _serve(rng: random.Random, toward: Literal["left", "right"]) -> tuple[int, int, int, int]:
    """Return (ball_x, ball_y, ball_vx, ball_vy) for a fresh serve.

    The ball starts at the center. Horizontal direction is determined by
    ``toward``; vertical direction is random.
    """
    bx = C.PLAY_W // 2
    by = C.PLAY_H // 2
    vx = -1 if toward == "left" else 1
    vy = rng.choice([-1, 1])
    return bx, by, vx, vy


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def new_game(rng: random.Random) -> GameState:
    """Create a fresh game. The ball is at center; serve direction is random."""
    bx, by, vx, vy = _serve(rng, rng.choice(["left", "right"]))
    return GameState(
        ball_x=bx,
        ball_y=by,
        ball_vx=vx,
        ball_vy=vy,
        left_y=_center_y(),
        right_y=_center_y(),
        started=False,
    )


def move_player(state: GameState, direction: int) -> GameState:
    """Move the left (human) paddle by ``direction`` (+1 down, -1 up).

    Clamps so the paddle cannot leave the court. Ignored when paused/over.
    """
    if state.game_over or state.paused:
        return state
    return replace(state, left_y=_clamp_paddle(state.left_y + direction))


def toggle_pause(state: GameState) -> GameState:
    """Flip the paused flag; no-op when game is over."""
    if state.game_over:
        return state
    return replace(state, paused=not state.paused)


def start(state: GameState) -> GameState:
    """Mark the game as started (space key). No-op once started."""
    if state.started:
        return state
    return replace(state, started=True)


def _ai_step(state: GameState) -> int:
    """Return the new right_y after the AI moves toward the ball.

    The AI moves at most ``C.AI_SPEED`` cells per tick so it can be beaten.
    """
    paddle_center = state.right_y + C.PADDLE_H // 2
    diff = state.ball_y - paddle_center
    step = max(-C.AI_SPEED, min(C.AI_SPEED, diff))
    return _clamp_paddle(state.right_y + step)


def tick(state: GameState, rng: random.Random) -> GameState:
    """Advance the ball one step, move the AI paddle, and resolve collisions.

    Returns a new :class:`GameState`. The injected ``rng`` is used only when
    a point is scored and the ball is re-served.
    """
    if state.game_over or state.paused or not state.started:
        return state

    bx = state.ball_x
    by = state.ball_y
    vx = state.ball_vx
    vy = state.ball_vy
    left_y = state.left_y
    right_y = state.right_y
    left_score = state.left_score
    right_score = state.right_score

    # Move AI paddle before ball collision so the paddle is already updated
    # when we check for a hit on the right side.
    right_y = _ai_step(state)

    # --- Vertical movement ---
    ny = by + vy
    if ny < 0:
        vy = -vy          # top wall
        ny = 0
    elif ny >= C.PLAY_H:
        vy = -vy          # bottom wall
        ny = C.PLAY_H - 1

    # --- Horizontal movement ---
    nx = bx + vx

    # Left paddle hit: ball moving left and would enter or pass paddle column.
    if vx == -1 and nx <= C.LEFT_PADDLE_X:
        if left_y <= ny < left_y + C.PADDLE_H:
            # Reflect horizontally; vary vertical angle based on hit position.
            vx = 1
            nx = C.LEFT_PADDLE_X + 1
            hit_offset = ny - (left_y + C.PADDLE_H // 2)
            if hit_offset < 0:
                vy = -1
            elif hit_offset > 0:
                vy = 1
            # else keep current vy
        elif nx < C.LEFT_PADDLE_X:
            # Ball passed the left paddle — right side scores.
            right_score += 1
            if right_score >= C.WIN_SCORE:
                return replace(
                    state,
                    ball_x=bx, ball_y=by,
                    left_score=left_score,
                    right_score=right_score,
                    right_y=right_y,
                    game_over=True,
                    winner="CPU",
                )
            nbx, nby, nvx, nvy = _serve(rng, "left")
            return replace(
                state,
                ball_x=nbx, ball_y=nby,
                ball_vx=nvx, ball_vy=nvy,
                left_score=left_score,
                right_score=right_score,
                right_y=right_y,
                started=False,
            )

    # Right paddle hit: ball moving right and would enter or pass paddle column.
    elif vx == 1 and nx >= C.RIGHT_PADDLE_X:
        if right_y <= ny < right_y + C.PADDLE_H:
            # Reflect horizontally; vary vertical angle based on hit position.
            vx = -1
            nx = C.RIGHT_PADDLE_X - 1
            hit_offset = ny - (right_y + C.PADDLE_H // 2)
            if hit_offset < 0:
                vy = -1
            elif hit_offset > 0:
                vy = 1
        elif nx > C.RIGHT_PADDLE_X:
            # Ball passed the right paddle — left side scores.
            left_score += 1
            if left_score >= C.WIN_SCORE:
                return replace(
                    state,
                    ball_x=bx, ball_y=by,
                    left_score=left_score,
                    right_score=right_score,
                    right_y=right_y,
                    game_over=True,
                    winner="Player",
                )
            nbx, nby, nvx, nvy = _serve(rng, "right")
            return replace(
                state,
                ball_x=nbx, ball_y=nby,
                ball_vx=nvx, ball_vy=nvy,
                left_score=left_score,
                right_score=right_score,
                right_y=right_y,
                started=False,
            )

    return replace(
        state,
        ball_x=nx,
        ball_y=ny,
        ball_vx=vx,
        ball_vy=vy,
        right_y=right_y,
        left_score=left_score,
        right_score=right_score,
    )

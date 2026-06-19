"""Immutable Breakout state and the transitions that drive it.

Like the Tetris core, every transition returns a new :class:`GameState`. The
ball advances one cell per axis each tick; collisions are resolved per axis so a
brick hit reflects the correct component of the velocity.
"""
from __future__ import annotations

from dataclasses import dataclass, replace
from typing import FrozenSet, Optional, Tuple

import config as C

Brick = Tuple[int, int]  # (brick_row, brick_col)


@dataclass(frozen=True)
class Ball:
    x: int
    y: int
    vx: int
    vy: int


@dataclass(frozen=True)
class GameState:
    paddle_x: int           # left edge of the paddle
    ball: Ball
    bricks: FrozenSet[Brick]
    score: int = 0
    lives: int = C.START_LIVES
    level: int = 1
    launched: bool = False   # False while the ball rests on the paddle
    game_over: bool = False


def _all_bricks() -> FrozenSet[Brick]:
    return frozenset(
        (r, c) for r in range(C.BRICK_ROWS) for c in range(C.BRICK_COLS)
    )


def _rest_ball(paddle_x: int) -> Ball:
    """Ball parked on top of the paddle, aimed up-left once launched."""
    return Ball(x=paddle_x + C.PADDLE_W // 2, y=C.PADDLE_ROW - 1, vx=-1, vy=-1)


def new_game() -> GameState:
    paddle_x = (C.PLAY_W - C.PADDLE_W) // 2
    return GameState(
        paddle_x=paddle_x,
        ball=_rest_ball(paddle_x),
        bricks=_all_bricks(),
    )


def _next_level(state: GameState) -> GameState:
    """Refill the brick field and reset the ball for the next level."""
    paddle_x = (C.PLAY_W - C.PADDLE_W) // 2
    return replace(
        state,
        paddle_x=paddle_x,
        ball=_rest_ball(paddle_x),
        bricks=_all_bricks(),
        level=state.level + 1,
        launched=False,
    )


def _clamp_paddle(x: int) -> int:
    return max(0, min(C.PLAY_W - C.PADDLE_W, x))


def move_paddle(state: GameState, dx: int) -> GameState:
    """Slide the paddle; a resting ball follows it so aiming stays intuitive."""
    if state.game_over:
        return state
    paddle_x = _clamp_paddle(state.paddle_x + dx)
    ball = state.ball
    if not state.launched:
        ball = replace(ball, x=paddle_x + C.PADDLE_W // 2)
    return replace(state, paddle_x=paddle_x, ball=ball)


def launch(state: GameState) -> GameState:
    """Release the ball from the paddle."""
    if state.game_over or state.launched:
        return state
    return replace(state, launched=True, ball=replace(state.ball, vx=-1, vy=-1))


def brick_at(bricks: FrozenSet[Brick], x: int, y: int) -> Optional[Brick]:
    """Return the brick occupying cell ``(x, y)`` or ``None``."""
    if y < C.BRICK_TOP or y >= C.BRICK_TOP + C.BRICK_ROWS:
        return None
    row = y - C.BRICK_TOP
    col = x // C.BRICK_W
    brick = (row, col)
    return brick if brick in bricks else None


def _lose_life(state: GameState) -> GameState:
    """Drop a life; end the game at zero, otherwise re-park the ball."""
    lives = state.lives - 1
    if lives <= 0:
        return replace(state, lives=0, launched=False, game_over=True)
    return replace(
        state, lives=lives, launched=False, ball=_rest_ball(state.paddle_x)
    )


def tick(state: GameState) -> GameState:
    """Advance the ball one step and resolve every collision."""
    if state.game_over or not state.launched:
        return state

    bricks = state.bricks
    score = state.score
    x, y, vx, vy = state.ball.x, state.ball.y, state.ball.vx, state.ball.vy

    # --- Horizontal step ---
    nx = x + vx
    if nx < 0 or nx >= C.PLAY_W:
        vx = -vx  # bounce off a side wall
    else:
        hit = brick_at(bricks, nx, y)
        if hit is not None:
            bricks = bricks - {hit}
            score += C.POINTS_PER_BRICK
            vx = -vx
        else:
            x = nx  # move horizontally

    # --- Vertical step ---
    ny = y + vy
    if ny < 0:
        vy = -vy  # bounce off the ceiling
    elif ny == C.PADDLE_ROW and state.paddle_x <= x < state.paddle_x + C.PADDLE_W:
        vy = -vy  # bounce off the paddle
        centre = state.paddle_x + C.PADDLE_W // 2
        if x < centre:
            vx = -1
        elif x > centre:
            vx = 1
    elif ny >= C.PLAY_H:
        # Missed the paddle. Returning the original state discards this tick's
        # horizontal step, which is safe only because a horizontal brick-break
        # requires y within the brick rows and the miss requires ny past the
        # floor -- these cannot co-occur while BRICK_TOP + BRICK_ROWS < PLAY_H.
        return _lose_life(state)
    else:
        hit = brick_at(bricks, x, ny)
        if hit is not None:
            bricks = bricks - {hit}
            score += C.POINTS_PER_BRICK
            vy = -vy
        else:
            y = ny  # move vertically

    state = replace(state, ball=Ball(x=x, y=y, vx=vx, vy=vy), bricks=bricks, score=score)

    if not bricks:
        return _next_level(state)
    return state

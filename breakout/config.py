"""Tunable constants for the Breakout playfield, bricks, and ball.

Coordinates use one terminal character per cell. The ball moves on an integer
grid one cell at a time on each axis, which keeps collision handling simple and
free of tunneling.
"""
from __future__ import annotations

# Playfield size in cells (interior, excluding the border).
PLAY_W = 40
PLAY_H = 24

# Paddle sits on the bottom interior row.
PADDLE_W = 8
PADDLE_ROW = PLAY_H - 1
PADDLE_STEP = 2  # cells moved per key press

# Brick field. BRICK_COLS * BRICK_W must equal PLAY_W so bricks tile exactly.
BRICK_COLS = 8
BRICK_W = PLAY_W // BRICK_COLS  # 5
BRICK_ROWS = 6
BRICK_TOP = 2  # first brick row (leaves a gap below the ceiling)

# Truecolor RGB per brick row, from top to bottom.
BRICK_RGB = (
    (240, 60, 60),    # red
    (240, 150, 40),   # orange
    (240, 220, 40),   # yellow
    (60, 220, 80),    # green
    (60, 160, 240),   # blue
    (170, 80, 240),   # purple
)

POINTS_PER_BRICK = 10
START_LIVES = 3

# Gravity / ball-step timing (seconds between ball ticks).
BASE_TICK = 0.09
MIN_TICK = 0.035
LEVEL_SPEEDUP = 0.008  # each level shortens the tick

assert BRICK_COLS * BRICK_W == PLAY_W, "bricks must tile the playfield exactly"
assert len(BRICK_RGB) >= BRICK_ROWS, "need one colour per brick row"

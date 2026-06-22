"""Tunable constants for the Pong playfield, paddles, and ball.

Coordinates use one terminal character per cell. The ball moves on an integer
grid one cell at a time on each tick, keeping collision handling simple.
"""
from __future__ import annotations

# Playfield size in cells (interior, excluding the border).
PLAY_W = 60
PLAY_H = 24

# Paddle dimensions and movement speed.
PADDLE_H = 5          # cells tall
PADDLE_STEP = 1       # cells moved per key press
AI_SPEED = 1          # max cells the AI paddle moves per tick (beatable)

# Paddle x positions (fixed columns inside the court).
LEFT_PADDLE_X = 1
RIGHT_PADDLE_X = PLAY_W - 2  # one cell from the right interior edge

# Win condition.
WIN_SCORE = 7

# Ball timing (seconds between ticks).
BALL_TICK = 0.07

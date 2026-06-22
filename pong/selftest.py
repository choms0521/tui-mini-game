"""Headless logic checks for the Pong core (no terminal required).

Run with ``python selftest.py``. Exercises wall bounces, paddle bounces,
scoring, re-serve, player paddle clamping, AI tracking, win detection,
immutability, and the render string builder.
"""
from __future__ import annotations

import random

import config as C
import game as G


def check(condition: bool, label: str) -> None:
    if not condition:
        raise AssertionError(f"FAILED: {label}")
    print(f"ok - {label}")


def _state(
    bx: int,
    by: int,
    vx: int,
    vy: int,
    left_y: int | None = None,
    right_y: int | None = None,
    left_score: int = 0,
    right_score: int = 0,
    started: bool = True,
) -> G.GameState:
    """Build a test GameState without going through new_game()."""
    if left_y is None:
        left_y = (C.PLAY_H - C.PADDLE_H) // 2
    if right_y is None:
        right_y = (C.PLAY_H - C.PADDLE_H) // 2
    return G.GameState(
        ball_x=bx,
        ball_y=by,
        ball_vx=vx,
        ball_vy=vy,
        left_y=left_y,
        right_y=right_y,
        left_score=left_score,
        right_score=right_score,
        started=started,
    )


# Use a fixed seed so all tests are deterministic.
_RNG = random.Random(42)


def test_top_wall_bounce() -> None:
    """Ball moving into the top wall should reverse vertical velocity."""
    s = _state(bx=C.PLAY_W // 2, by=0, vx=1, vy=-1)
    after = G.tick(s, _RNG)
    check(after.ball_vy == 1, "top wall: vy flips to positive")
    check(after.ball_y == 0, "top wall: ball stays at row 0")


def test_bottom_wall_bounce() -> None:
    """Ball moving into the bottom wall should reverse vertical velocity."""
    s = _state(bx=C.PLAY_W // 2, by=C.PLAY_H - 1, vx=1, vy=1)
    after = G.tick(s, _RNG)
    check(after.ball_vy == -1, "bottom wall: vy flips to negative")
    check(after.ball_y == C.PLAY_H - 1, "bottom wall: ball stays at bottom row")


def test_left_paddle_bounce() -> None:
    """Ball reaching the left paddle column should reverse horizontal velocity."""
    paddle_y = C.PLAY_H // 2 - C.PADDLE_H // 2
    # Place ball one step to the right of the paddle column, moving left.
    bx = C.LEFT_PADDLE_X + 1
    by = paddle_y + C.PADDLE_H // 2  # center of paddle
    s = _state(bx=bx, by=by, vx=-1, vy=0, left_y=paddle_y)
    after = G.tick(s, _RNG)
    check(after.ball_vx == 1, "left paddle bounce: vx flips to positive")


def test_right_paddle_bounce() -> None:
    """Ball reaching the right paddle column should reverse horizontal velocity."""
    paddle_y = C.PLAY_H // 2 - C.PADDLE_H // 2
    bx = C.RIGHT_PADDLE_X - 1
    by = paddle_y + C.PADDLE_H // 2
    s = _state(bx=bx, by=by, vx=1, vy=0, right_y=paddle_y)
    after = G.tick(s, _RNG)
    check(after.ball_vx == -1, "right paddle bounce: vx flips to negative")


def test_score_when_ball_passes_left_paddle() -> None:
    """Ball passing the left paddle without a hit should give right side a point."""
    # Put ball at left edge, moving left, paddle far away (top of court).
    s = _state(bx=C.LEFT_PADDLE_X, by=C.PLAY_H - 1, vx=-1, vy=0, left_y=0)
    # Paddle occupies rows 0..PADDLE_H-1; ball is at bottom row — miss.
    after = G.tick(s, _RNG)
    check(after.right_score == 1, "missed left paddle: right scores")
    check(not after.started, "after a point the ball is re-served (started=False)")
    check(not after.game_over, "game not over at score 1")


def test_score_when_ball_passes_right_paddle() -> None:
    """Ball passing the right paddle without a hit should give left side a point."""
    s = _state(bx=C.RIGHT_PADDLE_X, by=C.PLAY_H - 1, vx=1, vy=0, right_y=0)
    after = G.tick(s, _RNG)
    check(after.left_score == 1, "missed right paddle: left scores")
    check(not after.started, "after a point the ball is re-served (started=False)")


def test_ball_re_served_from_center() -> None:
    """After scoring the ball should restart near the court center."""
    s = _state(bx=C.LEFT_PADDLE_X, by=C.PLAY_H - 1, vx=-1, vy=0, left_y=0)
    after = G.tick(s, _RNG)
    mid_x = C.PLAY_W // 2
    mid_y = C.PLAY_H // 2
    check(
        abs(after.ball_x - mid_x) <= 1 and abs(after.ball_y - mid_y) <= 1,
        "re-served ball starts near center",
    )


def test_player_paddle_clamp_top() -> None:
    """Player paddle cannot move above row 0."""
    s = _state(bx=5, by=5, vx=1, vy=1, left_y=0)
    after = G.move_player(s, -1)
    check(after.left_y == 0, "player paddle clamped at top")


def test_player_paddle_clamp_bottom() -> None:
    """Player paddle cannot move below the last valid position."""
    max_y = C.PLAY_H - C.PADDLE_H
    s = _state(bx=5, by=5, vx=1, vy=1, left_y=max_y)
    after = G.move_player(s, 1)
    check(after.left_y == max_y, "player paddle clamped at bottom")


def test_ai_moves_toward_ball() -> None:
    """AI paddle should move its center closer to the ball each tick."""
    # Place AI paddle well above the ball so it must move down.
    ball_y = C.PLAY_H - 3
    right_y = 0
    s = _state(
        bx=C.RIGHT_PADDLE_X - 1,
        by=ball_y,
        vx=1,
        vy=0,
        right_y=right_y,
    )
    after = G.tick(s, _RNG)
    check(after.right_y > right_y, "AI paddle moves down toward a ball below it")


def test_win_detection_right() -> None:
    """CPU reaching WIN_SCORE should trigger game_over with winner='CPU'."""
    s = _state(
        bx=C.LEFT_PADDLE_X,
        by=C.PLAY_H - 1,
        vx=-1,
        vy=0,
        left_y=0,
        right_score=C.WIN_SCORE - 1,
    )
    after = G.tick(s, _RNG)
    check(after.game_over, "game over when CPU reaches win score")
    check(after.winner == "CPU", "winner is CPU")


def test_win_detection_player() -> None:
    """Player reaching WIN_SCORE should trigger game_over with winner='Player'."""
    s = _state(
        bx=C.RIGHT_PADDLE_X,
        by=C.PLAY_H - 1,
        vx=1,
        vy=0,
        right_y=0,
        left_score=C.WIN_SCORE - 1,
    )
    after = G.tick(s, _RNG)
    check(after.game_over, "game over when Player reaches win score")
    check(after.winner == "Player", "winner is Player")


def test_immutability() -> None:
    """tick() must return a new object; the original must be unchanged."""
    s = _state(bx=C.PLAY_W // 2, by=C.PLAY_H // 2, vx=1, vy=1)
    orig_x = s.ball_x
    orig_y = s.ball_y
    after = G.tick(s, _RNG)
    check(s.ball_x == orig_x and s.ball_y == orig_y, "original state unchanged after tick")
    check(after is not s, "tick returns a new object")


def test_render_builds_strings() -> None:
    """draw() and board_lines() must compose without raising exceptions."""
    import io
    from contextlib import redirect_stdout

    from blessed import Terminal
    import render as R

    term = Terminal(force_styling=True)
    rng = random.Random(0)
    s = G.new_game(rng)

    board = R.board_lines(term, s)
    # board_lines returns: top border + score line + PLAY_H interior + bottom border
    check(len(board) == C.PLAY_H + 3, "board_lines returns the correct number of lines")

    panel = R.panel_lines(term, s)
    check(any("PONG" in line for line in panel), "panel includes the title")

    # Exercise draw() for the three overlay states without a real TTY.
    started = G.start(s)
    paused = G.toggle_pause(started)
    over = G.GameState(
        ball_x=s.ball_x, ball_y=s.ball_y,
        ball_vx=s.ball_vx, ball_vy=s.ball_vy,
        left_y=s.left_y, right_y=s.right_y,
        game_over=True, winner="Player",
        started=True,
    )
    with redirect_stdout(io.StringIO()):
        R.draw(term, s)        # "press SPACE to serve" overlay
        R.draw(term, paused)   # "PAUSED" overlay
        R.draw(term, over)     # "Player wins!" overlay
    check(True, "draw() composes serve-hint, paused, and win frames without error")


def main() -> None:
    tests = [
        test_top_wall_bounce,
        test_bottom_wall_bounce,
        test_left_paddle_bounce,
        test_right_paddle_bounce,
        test_score_when_ball_passes_left_paddle,
        test_score_when_ball_passes_right_paddle,
        test_ball_re_served_from_center,
        test_player_paddle_clamp_top,
        test_player_paddle_clamp_bottom,
        test_ai_moves_toward_ball,
        test_win_detection_right,
        test_win_detection_player,
        test_immutability,
        test_render_builds_strings,
    ]
    for test in tests:
        test()
    print(f"\nAll {len(tests)} test groups passed.")


if __name__ == "__main__":
    main()

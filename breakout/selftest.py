"""Headless logic checks for the Breakout core (no terminal required).

Run with ``python selftest.py``. Exercises brick mapping, wall/ceiling/paddle
bounces, brick collisions with scoring, losing a life, game over, and clearing
a level, plus the rendering string builder.
"""
from __future__ import annotations

import config as C
import game as G


def check(condition: bool, label: str) -> None:
    if not condition:
        raise AssertionError(f"FAILED: {label}")
    print(f"ok - {label}")


def _state(x, y, vx, vy, paddle_x=16, bricks=None, lives=C.START_LIVES, launched=True):
    if bricks is None:
        bricks = frozenset({(0, 0), (5, 7)})  # two far-apart bricks
    return G.GameState(
        paddle_x=paddle_x,
        ball=G.Ball(x=x, y=y, vx=vx, vy=vy),
        bricks=bricks,
        lives=lives,
        launched=launched,
    )


def test_new_game_defaults() -> None:
    s = G.new_game()
    check(s.lives == C.START_LIVES, "new game starts with full lives")
    check(s.level == 1 and not s.launched and not s.game_over, "new game is level 1, unlaunched")
    check(len(s.bricks) == C.BRICK_ROWS * C.BRICK_COLS, "new game fills every brick")
    check(s.paddle_x == (C.PLAY_W - C.PADDLE_W) // 2, "paddle starts centred")
    check(s.ball.y == C.PADDLE_ROW - 1, "ball rests just above the paddle")


def test_brick_at_mapping() -> None:
    bricks = G._all_bricks()
    check(G.brick_at(bricks, 0, C.BRICK_TOP) == (0, 0), "top-left cell maps to brick (0,0)")
    check(G.brick_at(bricks, 7, C.BRICK_TOP + 1) == (1, 1), "cell maps to the right brick column")
    check(G.brick_at(bricks, 0, C.BRICK_TOP - 1) is None, "above the field has no brick")
    check(G.brick_at(bricks, 0, C.BRICK_TOP + C.BRICK_ROWS) is None, "below the field has no brick")
    check(G.brick_at(frozenset(), 0, C.BRICK_TOP) is None, "no bricks means no hit")


def test_launch_and_move() -> None:
    s = G.new_game()
    launched = G.launch(s)
    check(launched.launched, "space launches the ball")
    check(G.launch(launched) is launched, "launching twice is a no-op")

    moved = G.move_paddle(s, -C.PADDLE_STEP)
    check(moved.paddle_x == s.paddle_x - C.PADDLE_STEP, "paddle slides left")
    check(moved.ball.x == moved.paddle_x + C.PADDLE_W // 2, "resting ball follows the paddle")

    far_left = s
    for _ in range(C.PLAY_W):
        far_left = G.move_paddle(far_left, -C.PADDLE_STEP)
    check(far_left.paddle_x == 0, "paddle clamps at the left wall")
    far_right = s
    for _ in range(C.PLAY_W):
        far_right = G.move_paddle(far_right, C.PADDLE_STEP)
    check(far_right.paddle_x == C.PLAY_W - C.PADDLE_W, "paddle clamps at the right wall")


def test_ceiling_bounce() -> None:
    s = _state(x=20, y=0, vx=1, vy=-1)
    after = G.tick(s)
    check(after.ball.vy == 1, "ball bounces down off the ceiling")
    check(after.level == 1, "ceiling bounce does not trigger a level change")


def test_side_wall_bounce() -> None:
    s = _state(x=C.PLAY_W - 1, y=12, vx=1, vy=1)
    after = G.tick(s)
    check(after.ball.vx == -1, "ball bounces off the right wall")
    check(after.ball.x == C.PLAY_W - 1, "ball stays inside after a wall bounce")


def test_brick_collision_vertical() -> None:
    s = _state(x=2, y=3, vx=1, vy=-1)
    after = G.tick(s)
    check((0, 0) not in after.bricks, "a brick hit from below is removed")
    check(after.score == C.POINTS_PER_BRICK, "breaking a brick scores points")
    check(after.ball.vy == 1, "vertical hit reverses vertical velocity")
    check(len(after.bricks) == 1, "the other brick survives")


def test_brick_collision_horizontal() -> None:
    s = _state(x=4, y=2, vx=1, vy=-1, bricks=frozenset({(0, 1), (5, 7)}))
    after = G.tick(s)
    check((0, 1) not in after.bricks, "a brick hit from the side is removed")
    check(after.ball.vx == -1, "horizontal hit reverses horizontal velocity")
    check(after.score == C.POINTS_PER_BRICK, "side hit scores points")


def test_paddle_bounce_angle() -> None:
    left = G.tick(_state(x=18, y=22, vx=-1, vy=1))
    check(left.ball.vy == -1, "ball bounces up off the paddle")
    check(left.ball.vx == -1, "hitting left of centre sends the ball left")

    right = G.tick(_state(x=22, y=22, vx=1, vy=1))
    check(right.ball.vx == 1, "hitting right of centre sends the ball right")


def test_miss_loses_life() -> None:
    s = _state(x=2, y=C.PADDLE_ROW, vx=-1, vy=1, lives=3)
    after = G.tick(s)
    check(after.lives == 2, "missing the paddle costs a life")
    check(not after.launched, "the ball re-parks on the paddle after a miss")
    check(not after.game_over, "still in play with lives remaining")
    check(after.ball.y == C.PADDLE_ROW - 1, "the re-parked ball sits above the paddle")


def test_game_over_at_zero_lives() -> None:
    s = _state(x=2, y=C.PADDLE_ROW, vx=-1, vy=1, lives=1)
    after = G.tick(s)
    check(after.game_over and after.lives == 0, "losing the last life ends the game")


def test_clear_advances_level() -> None:
    s = _state(x=2, y=3, vx=1, vy=-1, bricks=frozenset({(0, 0)}))
    after = G.tick(s)
    check(after.level == 2, "clearing every brick advances to the next level")
    check(len(after.bricks) == C.BRICK_ROWS * C.BRICK_COLS, "the new level refills the bricks")
    check(not after.launched, "the next level starts with the ball parked")
    check(after.score == C.POINTS_PER_BRICK, "score carries over into the next level")


def test_render_builds_strings() -> None:
    import io
    from contextlib import redirect_stdout

    from blessed import Terminal
    import render as R

    term = Terminal(force_styling=True)
    s = G.new_game()
    board = R.board_lines(term, s)
    check(len(board) == C.PLAY_H + 2, "board renders all rows plus two borders")
    panel = R.panel_lines(term, s)
    check(any("BREAKOUT" in line for line in panel), "panel shows the title")

    launched = G.launch(s)
    over = G.GameState(paddle_x=s.paddle_x, ball=s.ball, bricks=s.bricks, game_over=True)
    with redirect_stdout(io.StringIO()):
        R.draw(term, s)          # unlaunched -> launch hint overlay
        R.draw(term, launched, paused=True)
        R.draw(term, over)       # game over overlay
    check(True, "draw() composes launch, paused, and game-over frames without error")


def main() -> None:
    tests = [
        test_new_game_defaults,
        test_brick_at_mapping,
        test_launch_and_move,
        test_ceiling_bounce,
        test_side_wall_bounce,
        test_brick_collision_vertical,
        test_brick_collision_horizontal,
        test_paddle_bounce_angle,
        test_miss_loses_life,
        test_game_over_at_zero_lives,
        test_clear_advances_level,
        test_render_builds_strings,
    ]
    for test in tests:
        test()
    print(f"\nAll {len(tests)} test groups passed.")


if __name__ == "__main__":
    main()

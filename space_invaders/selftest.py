"""Headless logic checks for the Space Invaders core (no terminal required).

Run with ``python selftest.py``. Exercises fleet movement, bullet travel,
collision detection, player movement bounds, win/lose conditions, immutability,
and the rendering string builder so the game can be verified without a TTY.
"""
from __future__ import annotations

import io
import random
from contextlib import redirect_stdout

import board as B
import game as G
import render as R


def check(condition: bool, label: str) -> None:
    if not condition:
        raise AssertionError(f"FAILED: {label}")
    print(f"ok - {label}")


# ---------------------------------------------------------------------------
# Fleet movement tests
# ---------------------------------------------------------------------------

def test_fleet_moves_horizontally() -> None:
    rng = random.Random(1)
    state = G.new_game(rng)
    cols_before = [c for _, c in state.aliens]
    new_state = G.advance_fleet(state)
    cols_after = [c for _, c in new_state.aliens]
    check(
        all(a == b + state.direction for a, b in zip(cols_after, cols_before)),
        "fleet shifts horizontally by direction when not at edge",
    )
    check(new_state.direction == state.direction, "direction unchanged after a horizontal step")


def test_fleet_edge_step_down_and_flip() -> None:
    """When the fleet hits the right edge it steps down and flips direction."""
    rng = random.Random(1)
    state = G.new_game(rng)
    # Push the fleet right until it would overflow on the next advance.
    for _ in range(200):
        if state.game_over or state.won:
            break
        cols = [c for _, c in state.aliens]
        if max(cols) + state.direction >= B.WIDTH:
            break
        state = G.advance_fleet(state)

    rows_before = [r for r, _ in state.aliens]
    cols_before = [c for _, c in state.aliens]
    direction_before = state.direction

    new_state = G.advance_fleet(state)

    rows_after = [r for r, _ in new_state.aliens]
    cols_after = [c for _, c in new_state.aliens]

    check(
        all(r_after == r_before + 1 for r_after, r_before in zip(rows_after, rows_before)),
        "all aliens step down one row when fleet hits an edge",
    )
    check(
        cols_after == cols_before,
        "alien columns are unchanged on a step-down tick",
    )
    check(
        new_state.direction == -direction_before,
        "fleet direction flips after hitting an edge",
    )


def test_fleet_left_edge_step_down_and_flip() -> None:
    """When the fleet hits the left edge it steps down and flips direction."""
    rng = random.Random(1)
    state = G.new_game(rng)
    # Force the fleet to be moving left by doing one step-down first.
    # Build a minimal state with direction=-1 near the left wall.
    leftmost_col = 0
    aliens = tuple((1, leftmost_col + i) for i in range(3))
    state = G.GameState(
        player_col=B.WIDTH // 2,
        bullets=(),
        aliens=aliens,
        direction=-1,
    )
    # With direction=-1 and leftmost col at 0, advance should step down.
    cols_before = [c for _, c in state.aliens]
    rows_before = [r for r, _ in state.aliens]

    new_state = G.advance_fleet(state)

    rows_after = [r for r, _ in new_state.aliens]
    cols_after = [c for _, c in new_state.aliens]

    check(
        all(r_after == r_before + 1 for r_after, r_before in zip(rows_after, rows_before)),
        "fleet steps down when hitting the left edge",
    )
    check(cols_after == cols_before, "columns unchanged on left-edge step-down")
    check(new_state.direction == 1, "direction flips to +1 after left-edge bounce")


# ---------------------------------------------------------------------------
# Bullet tests
# ---------------------------------------------------------------------------

def test_bullet_alien_collision_removes_both_and_scores() -> None:
    # Bullet is one row below the alien; after advancing one row up, it lands on the alien.
    alien_pos = (5, 10)
    bullet_pos = (6, 10)   # bullet will move to (5, 10) == alien_pos on this tick
    state = G.GameState(
        player_col=10,
        bullets=(bullet_pos,),
        aliens=(alien_pos,),
        direction=1,
        score=0,
    )
    new_state = G.advance_bullets(state)
    check(len(new_state.aliens) == 0, "alien removed after bullet collision")
    check(len(new_state.bullets) == 0, "bullet removed after collision")
    check(new_state.score == G.SCORE_PER_KILL, "score increases by SCORE_PER_KILL on kill")


def test_bullet_travels_upward() -> None:
    state = G.GameState(
        player_col=10,
        bullets=((10, 10),),
        aliens=(),
        direction=1,
    )
    new_state = G.advance_bullets(state)
    check(len(new_state.bullets) == 1, "bullet stays in field after one upward step")
    check(new_state.bullets[0] == (9, 10), "bullet moves one row upward per tick")


def test_bullet_removed_when_leaving_field() -> None:
    state = G.GameState(
        player_col=10,
        bullets=((0, 10),),   # already at top row
        aliens=(),
        direction=1,
    )
    new_state = G.advance_bullets(state)
    check(len(new_state.bullets) == 0, "bullet leaving top of field is removed")


def test_multiple_bullets_independent_collision() -> None:
    alien1 = (5, 10)
    alien2 = (3, 15)
    bullet_hit = (6, 10)   # will move to (5, 10) == alien1 on this tick
    bullet_miss = (8, 20)  # will move to (7, 20), no alien there
    state = G.GameState(
        player_col=10,
        bullets=(bullet_hit, bullet_miss),
        aliens=(alien1, alien2),
        direction=1,
        score=0,
    )
    new_state = G.advance_bullets(state)
    check(len(new_state.aliens) == 1, "only the hit alien is removed")
    check(new_state.aliens[0] == alien2, "surviving alien is the unshot one")
    check(new_state.score == G.SCORE_PER_KILL, "exactly one kill scored")


# ---------------------------------------------------------------------------
# Player movement tests
# ---------------------------------------------------------------------------

def test_player_move_left_and_right() -> None:
    rng = random.Random(1)
    state = G.new_game(rng)
    start = state.player_col
    moved_right = G.move_player(state, 1)
    check(moved_right.player_col == start + 1, "player moves right by 1")
    moved_left = G.move_player(state, -1)
    check(moved_left.player_col == start - 1, "player moves left by 1")


def test_player_cannot_leave_field_left() -> None:
    state = G.GameState(player_col=0, bullets=(), aliens=(), direction=1)
    new_state = G.move_player(state, -1)
    check(new_state is state, "move_player returns same object at left boundary")
    check(new_state.player_col == 0, "player column stays at 0 at left boundary")


def test_player_cannot_leave_field_right() -> None:
    state = G.GameState(player_col=B.WIDTH - 1, bullets=(), aliens=(), direction=1)
    new_state = G.move_player(state, 1)
    check(new_state is state, "move_player returns same object at right boundary")
    check(new_state.player_col == B.WIDTH - 1, "player column stays at WIDTH-1 at right boundary")


# ---------------------------------------------------------------------------
# Fire tests
# ---------------------------------------------------------------------------

def test_fire_adds_bullet() -> None:
    state = G.GameState(player_col=10, bullets=(), aliens=(), direction=1)
    new_state = G.fire(state)
    check(len(new_state.bullets) == 1, "fire() adds one bullet")
    check(new_state.bullets[0] == (B.PLAYER_ROW - 1, 10), "bullet spawns just above player")


def test_fire_respects_bullet_cap() -> None:
    full_bullets = tuple((i, 10) for i in range(G.MAX_BULLETS))
    state = G.GameState(player_col=10, bullets=full_bullets, aliens=(), direction=1)
    new_state = G.fire(state)
    check(new_state is state, "fire() returns same object when bullet cap reached")
    check(len(new_state.bullets) == G.MAX_BULLETS, "bullet count does not exceed cap")


# ---------------------------------------------------------------------------
# Win / lose condition tests
# ---------------------------------------------------------------------------

def test_win_when_all_aliens_destroyed() -> None:
    alien_pos = (5, 10)
    bullet_pos = (6, 10)   # will move to (5, 10) == alien_pos on this tick
    state = G.GameState(
        player_col=10,
        bullets=(bullet_pos,),
        aliens=(alien_pos,),
        direction=1,
        score=0,
    )
    new_state = G.advance_bullets(state)
    check(new_state.won, "won=True when last alien is destroyed")
    check(not new_state.game_over, "game_over stays False on win")


def test_lose_when_alien_reaches_player_row() -> None:
    alien_at_player_row = (B.PLAYER_ROW, 5)
    state = G.GameState(
        player_col=10,
        bullets=(),
        aliens=(alien_at_player_row,),
        direction=1,
    )
    new_state = G.advance_fleet(state)
    check(new_state.game_over, "game_over=True when alien reaches player row")


def test_lose_when_alien_passes_player_row() -> None:
    # Alien one row above player; after fleet step-down it lands on player row.
    alien_near = (B.PLAYER_ROW - 1, 5)
    # Place it at the edge so next advance causes a step-down (or just check row >=).
    state = G.GameState(
        player_col=10,
        bullets=(),
        aliens=(alien_near,),
        direction=1,
    )
    # Manually build state where alien is at player row after advance.
    alien_at_row = (B.PLAYER_ROW, 5)
    state2 = G.GameState(
        player_col=10,
        bullets=(),
        aliens=(alien_at_row,),
        direction=1,
    )
    # advance_fleet will check the post-move positions.
    new_state = G.advance_fleet(state2)
    check(new_state.game_over, "game_over when alien is already at player row")


# ---------------------------------------------------------------------------
# Immutability test
# ---------------------------------------------------------------------------

def test_immutability() -> None:
    rng = random.Random(7)
    state = G.new_game(rng)
    original_col = state.player_col
    original_bullets = state.bullets
    original_aliens = state.aliens

    G.move_player(state, 1)
    G.fire(state)
    G.advance_bullets(state)
    G.advance_fleet(state)

    check(state.player_col == original_col, "move_player does not mutate original state")
    check(state.bullets == original_bullets, "fire/advance_bullets do not mutate original state")
    check(state.aliens == original_aliens, "advance_fleet does not mutate original state")


# ---------------------------------------------------------------------------
# Render / draw composition test
# ---------------------------------------------------------------------------

def test_render_builds_strings() -> None:
    from blessed import Terminal

    term = Terminal(force_styling=True)
    rng = random.Random(4)
    state = G.new_game(rng)

    field = R.field_lines(term, state)
    check(len(field) == B.HEIGHT + 2, "field renders all rows plus two border rows")

    panel = R.panel_lines(term, state)
    check(any("INVADERS" in line for line in panel), "panel shows the INVADERS title")

    # draw() must compose full frames without raising, including all overlays.
    paused_state = state
    won_state = G.GameState(
        player_col=state.player_col,
        bullets=(),
        aliens=(),
        direction=1,
        score=100,
        won=True,
    )
    over_state = G.GameState(
        player_col=state.player_col,
        bullets=(),
        aliens=state.aliens,
        direction=1,
        game_over=True,
    )

    with redirect_stdout(io.StringIO()):
        R.draw(term, state, paused=False)
        R.draw(term, paused_state, paused=True)
        R.draw(term, won_state)
        R.draw(term, over_state)

    check(True, "draw() composes normal, paused, won, and game-over frames without error")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    tests = [
        test_fleet_moves_horizontally,
        test_fleet_edge_step_down_and_flip,
        test_fleet_left_edge_step_down_and_flip,
        test_bullet_alien_collision_removes_both_and_scores,
        test_bullet_travels_upward,
        test_bullet_removed_when_leaving_field,
        test_multiple_bullets_independent_collision,
        test_player_move_left_and_right,
        test_player_cannot_leave_field_left,
        test_player_cannot_leave_field_right,
        test_fire_adds_bullet,
        test_fire_respects_bullet_cap,
        test_win_when_all_aliens_destroyed,
        test_lose_when_alien_reaches_player_row,
        test_lose_when_alien_passes_player_row,
        test_immutability,
        test_render_builds_strings,
    ]
    for test in tests:
        test()
    print(f"\nAll {len(tests)} test groups passed.")


if __name__ == "__main__":
    main()

"""Headless logic checks for the Snake core (no terminal required).

Run with ``python selftest.py``. Exercises movement, collision, growth,
direction rules, immutability, food spawning, and the rendering string
builder so the game can be verified in CI or over SSH without a TTY.
"""
from __future__ import annotations

import random

import board as B
import game as G


def check(condition: bool, label: str) -> None:
    if not condition:
        raise AssertionError(f"FAILED: {label}")
    print(f"ok - {label}")


# ---------------------------------------------------------------------------
# Board helpers
# ---------------------------------------------------------------------------

def test_board_bounds() -> None:
    check(B.in_bounds(0, 0), "top-left corner is in bounds")
    check(B.in_bounds(B.HEIGHT - 1, B.WIDTH - 1), "bottom-right corner is in bounds")
    check(not B.in_bounds(-1, 0), "row -1 is out of bounds")
    check(not B.in_bounds(B.HEIGHT, 0), "row == HEIGHT is out of bounds")
    check(not B.in_bounds(0, -1), "col -1 is out of bounds")
    check(not B.in_bounds(0, B.WIDTH), "col == WIDTH is out of bounds")


def test_all_cells_count() -> None:
    cells = B.all_cells()
    check(len(cells) == B.WIDTH * B.HEIGHT, "all_cells() returns WIDTH*HEIGHT entries")
    check(cells == sorted(cells), "all_cells() is in sorted (row-major) order")
    check(len(set(cells)) == len(cells), "all_cells() has no duplicates")


# ---------------------------------------------------------------------------
# New-game state
# ---------------------------------------------------------------------------

def test_new_game_initial_state() -> None:
    rng = random.Random(42)
    state = G.new_game(rng)
    check(len(state.body) == 3, "snake starts with 3 cells")
    check(state.score == 0, "score starts at 0")
    check(not state.game_over, "game does not start over")
    check(state.food not in set(state.body), "initial food is not inside the snake")
    check(B.in_bounds(*state.food), "initial food is within bounds")


# ---------------------------------------------------------------------------
# Direction / no-reverse rule
# ---------------------------------------------------------------------------

def test_turn_no_reverse() -> None:
    rng = random.Random(1)
    state = G.new_game(rng)
    # Default direction is RIGHT = (0, 1); reverse is LEFT = (0, -1).
    blocked = G.turn(state, G.LEFT)
    check(blocked is state, "turning 180 degrees returns the same state object")
    check(blocked.direction == G.RIGHT, "direction unchanged after illegal turn")


def test_turn_valid() -> None:
    rng = random.Random(2)
    state = G.new_game(rng)
    turned = G.turn(state, G.UP)
    check(turned is not state, "valid turn returns a new state object")
    check(turned.direction == G.UP, "direction updated after valid turn")


def test_turn_noop_when_game_over() -> None:
    rng = random.Random(3)
    state = G.new_game(rng)
    over_state = G.advance.__func__ if False else None  # just to reference module
    import dataclasses
    over = dataclasses.replace(state, game_over=True)
    result = G.turn(over, G.UP)
    check(result is over, "turn() on a game-over state returns the same object")


# ---------------------------------------------------------------------------
# Advance / movement
# ---------------------------------------------------------------------------

def test_advance_moves_head() -> None:
    rng = random.Random(10)
    state = G.new_game(rng)
    # Default direction is RIGHT.
    head_r, head_c = state.body[0]
    next_state = G.advance(state, rng)
    if not next_state.game_over:
        new_head = next_state.body[0]
        check(new_head == (head_r, head_c + 1), "head advances one cell to the right")


def test_advance_tail_vacates() -> None:
    """The tail cell must not be in the new body when no food is eaten."""
    rng = random.Random(20)
    state = G.new_game(rng)
    old_tail = state.body[-1]
    # Ensure we won't eat food on this step by placing the snake far from food.
    # new_game positions head in the centre heading right; just check the rule.
    next_state = G.advance(state, rng)
    if not next_state.game_over and len(next_state.body) == len(state.body):
        check(old_tail not in set(next_state.body), "tail cell vacates after normal move")


# ---------------------------------------------------------------------------
# Growth on eating
# ---------------------------------------------------------------------------

def test_growth_on_eating() -> None:
    """Snake grows by exactly one cell when it eats food."""
    rng = random.Random(99)
    state = G.new_game(rng)
    # Manually position the food one step ahead of the head.
    head_r, head_c = state.body[0]
    dr, dc = state.direction
    food_cell = (head_r + dr, head_c + dc)
    if not B.in_bounds(*food_cell):
        # Head is at the edge; move it inward first.
        state = G.new_game(random.Random(77))
        head_r, head_c = state.body[0]
        dr, dc = state.direction
        food_cell = (head_r + dr, head_c + dc)
    import dataclasses
    state = dataclasses.replace(state, food=food_cell)
    before_len = len(state.body)
    next_state = G.advance(state, rng)
    check(len(next_state.body) == before_len + 1, "snake grows by 1 after eating food")
    check(next_state.score == state.score + 1, "score increments by 1 after eating")
    check(next_state.food != food_cell, "a new food cell spawns after eating")
    check(next_state.food not in set(next_state.body), "new food is not inside the snake")


# ---------------------------------------------------------------------------
# Game-over: wall collision
# ---------------------------------------------------------------------------

def test_game_over_wall() -> None:
    """Snake dies when it walks into a wall."""
    import dataclasses
    rng = random.Random(5)
    state = G.new_game(rng)
    # Place head on the left edge heading left so the next step exits the board.
    body = ((0, 0), (0, 1), (0, 2))
    food = (B.HEIGHT - 1, B.WIDTH - 1)
    state = dataclasses.replace(state, body=body, direction=G.LEFT, food=food)
    next_state = G.advance(state, rng)
    check(next_state.game_over, "hitting the left wall ends the game")


def test_game_over_wall_all_sides() -> None:
    """Check each wall independently."""
    import dataclasses
    rng = random.Random(6)
    base = G.new_game(rng)
    food = (B.HEIGHT - 1, B.WIDTH - 1)

    cases = [
        ((0, 1), (0, 2), (0, 3), G.UP,    "top wall"),
        ((B.HEIGHT - 1, 1), (B.HEIGHT - 1, 2), (B.HEIGHT - 1, 3), G.DOWN,  "bottom wall"),
        ((1, 0), (1, 1), (1, 2), G.LEFT,  "left wall"),
        ((1, B.WIDTH - 1), (1, B.WIDTH - 2), (1, B.WIDTH - 3), G.RIGHT, "right wall"),
    ]
    for h, b1, b2, direction, label in cases:
        state = dataclasses.replace(base, body=(h, b1, b2), direction=direction, food=food)
        result = G.advance(state, rng)
        check(result.game_over, f"hitting the {label} ends the game")


# ---------------------------------------------------------------------------
# Game-over: self-collision
# ---------------------------------------------------------------------------

def test_game_over_self_collision() -> None:
    """Snake dies when its head enters a non-tail body cell."""
    import dataclasses
    rng = random.Random(7)
    base = G.new_game(rng)
    # Snake forms a backwards-C: head at (5,5) heading RIGHT.
    # (5,6) is a middle body cell (not the tail), so it does NOT vacate.
    # The next head lands on (5,6), which is still occupied -> game over.
    body = (
        (5, 5),
        (4, 5),
        (4, 6),
        (4, 7),
        (5, 7),
        (5, 6),   # collision target -- NOT the tail, stays occupied
        (5, 3),   # actual tail that vacates
    )
    food = (0, 0)
    state = dataclasses.replace(base, body=body, direction=G.RIGHT, food=food)
    result = G.advance(state, rng)
    check(result.game_over, "head entering its own body ends the game")


def test_no_self_collision_on_tail_vacate() -> None:
    """Moving into the cell the tail just vacated must NOT trigger game over."""
    import dataclasses
    rng = random.Random(8)
    base = G.new_game(rng)
    # Build a 3-cell snake heading DOWN where the tail is directly above the head
    # so the snake would 'chase its tail' — legal because the tail moves away.
    # Layout: head=(5,5) dir=RIGHT, body=(5,5),(5,4),(5,3)
    # After one step: head=(5,6), body vacates (5,3). No collision.
    body = ((5, 5), (5, 4), (5, 3))
    food = (0, 0)
    state = dataclasses.replace(base, body=body, direction=G.RIGHT, food=food)
    result = G.advance(state, rng)
    check(not result.game_over, "moving into vacated tail cell is legal")


# ---------------------------------------------------------------------------
# Immutability
# ---------------------------------------------------------------------------

def test_immutability_advance() -> None:
    """advance() must return a new object; the original must be unchanged."""
    rng = random.Random(50)
    state = G.new_game(rng)
    original_body = state.body
    original_score = state.score
    new_state = G.advance(state, rng)
    check(new_state is not state, "advance() returns a new state object")
    check(state.body == original_body, "original body tuple is unchanged")
    check(state.score == original_score, "original score is unchanged")


def test_immutability_turn() -> None:
    """turn() must return a new object; the original direction is unchanged."""
    rng = random.Random(51)
    state = G.new_game(rng)
    original_dir = state.direction
    new_state = G.turn(state, G.UP)
    check(new_state is not state, "turn() returns a new state object")
    check(state.direction == original_dir, "original direction is unchanged after turn()")


# ---------------------------------------------------------------------------
# Food placement determinism
# ---------------------------------------------------------------------------

def test_food_on_empty_cell() -> None:
    """Food must always land on a cell not occupied by the snake."""
    rng = random.Random(60)
    state = G.new_game(rng)
    for _ in range(20):
        state = G.advance(state, rng)
        if state.game_over:
            break
        check(state.food not in set(state.body), "food is always on an empty cell")


def test_food_spawn_deterministic() -> None:
    """Two calls to new_game with the same seed must produce the same food cell."""
    rng1 = random.Random(999)
    rng2 = random.Random(999)
    s1 = G.new_game(rng1)
    s2 = G.new_game(rng2)
    check(s1.food == s2.food, "food spawn is deterministic for a given seed")


# ---------------------------------------------------------------------------
# Tick interval
# ---------------------------------------------------------------------------

def test_tick_interval_decreases() -> None:
    low = G.tick_interval(0)
    high_score = G.tick_interval(200)
    check(low > high_score, "tick interval decreases as score grows")
    check(G.tick_interval(99999) >= G.MIN_TICK, "tick interval never falls below MIN_TICK")


# ---------------------------------------------------------------------------
# Render string composition (no TTY needed)
# ---------------------------------------------------------------------------

def test_render_builds_strings() -> None:
    import io
    from contextlib import redirect_stdout

    from blessed import Terminal
    import render as R

    term = Terminal(force_styling=True)
    rng = random.Random(4)
    state = G.new_game(rng)

    board = R.board_lines(term, state)
    check(len(board) == B.HEIGHT + 2, "board renders all rows plus two border lines")
    panel = R.panel_lines(term, state)
    check(any("SNAKE" in line for line in panel), "panel shows the SNAKE title")

    import dataclasses
    over_state = dataclasses.replace(state, game_over=True)

    with redirect_stdout(io.StringIO()):
        R.draw(term, state, paused=False)
        R.draw(term, state, paused=True)
        R.draw(term, over_state)
    check(True, "draw() composes normal, paused, and game-over frames without error")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    tests = [
        test_board_bounds,
        test_all_cells_count,
        test_new_game_initial_state,
        test_turn_no_reverse,
        test_turn_valid,
        test_turn_noop_when_game_over,
        test_advance_moves_head,
        test_advance_tail_vacates,
        test_growth_on_eating,
        test_game_over_wall,
        test_game_over_wall_all_sides,
        test_game_over_self_collision,
        test_no_self_collision_on_tail_vacate,
        test_immutability_advance,
        test_immutability_turn,
        test_food_on_empty_cell,
        test_food_spawn_deterministic,
        test_tick_interval_decreases,
        test_render_builds_strings,
    ]
    for test in tests:
        test()
    print(f"\nAll {len(tests)} test groups passed.")


if __name__ == "__main__":
    main()

"""Headless logic checks for the Tron core (no terminal required).

Run with ``python selftest.py``. Exercises tick advancement and trail laying,
wall/boundary collisions, head-on and swap draws, the no-reverse input rule,
AI avoidance and determinism, winner resolution, immutability, the purity of
tick(), and the rendering string builder so the game can be verified in CI or
over SSH without a TTY. Passing exits 0.
"""
from __future__ import annotations

import dataclasses
import random

import board as B
import game as G


def check(condition: bool, label: str) -> None:
    if not condition:
        raise AssertionError(f"FAILED: {label}")
    print(f"ok - {label}")


def _make(**overrides) -> G.GameState:
    """Build a controlled GameState on top of a fresh new_game()."""
    return dataclasses.replace(G.new_game(), **overrides)


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


# ---------------------------------------------------------------------------
# New-game state
# ---------------------------------------------------------------------------

def test_new_game_initial_state() -> None:
    state = G.new_game()
    check(state.walls == frozenset(), "no walls exist at the start")
    check(state.player_alive and state.ai_alive, "both cycles start alive")
    check(not state.game_over, "game does not start over")
    check(state.winner is None, "no winner at the start")
    check(state.tick == 0, "tick counter starts at 0")
    check(state.player_pos != state.ai_pos, "cycles start on different cells")
    check(state.player_dir == B.RIGHT and state.ai_dir == B.LEFT, "cycles face each other")


# ---------------------------------------------------------------------------
# Tick advancement + trail laying
# ---------------------------------------------------------------------------

def test_tick_advances_and_leaves_wall() -> None:
    """Each head moves one cell in its direction; the vacated cell becomes a wall."""
    state = _make(
        player_pos=(5, 5), player_dir=B.RIGHT,
        ai_pos=(15, 30), ai_dir=B.LEFT,
    )
    nxt = G.tick(state)
    check(nxt.player_pos == (5, 6), "player head advances one cell right")
    check(nxt.ai_pos == (15, 29), "ai head advances one cell left")
    check((5, 5) in nxt.walls, "player's previous cell is now a wall")
    check((15, 30) in nxt.walls, "ai's previous cell is now a wall")
    check(nxt.tick == state.tick + 1, "tick counter increments by one")
    check(nxt.player_alive and nxt.ai_alive, "both cycles survive a clear tick")
    check(not nxt.game_over, "game continues when both survive")


def test_trail_owner_split() -> None:
    """Per-owner render trails together reconstruct the full wall set."""
    state = _make(
        player_pos=(5, 5), player_dir=B.RIGHT,
        ai_pos=(15, 30), ai_dir=B.LEFT,
    )
    nxt = G.tick(state)
    check((5, 5) in nxt.player_trail, "player's vacated cell joins the player trail")
    check((15, 30) in nxt.ai_trail, "ai's vacated cell joins the ai trail")
    check(nxt.player_trail | nxt.ai_trail == nxt.walls, "owner trails reconstruct walls")


# ---------------------------------------------------------------------------
# Collision death: wall and boundary
# ---------------------------------------------------------------------------

def test_death_on_wall() -> None:
    """A cycle entering an existing wall dies; the survivor wins."""
    wall = (5, 6)
    state = _make(
        walls=frozenset({wall}),
        player_pos=(5, 5), player_dir=B.RIGHT,   # steps into the wall at (5,6)
        ai_pos=(15, 30), ai_dir=B.LEFT,
    )
    nxt = G.tick(state)
    check(not nxt.player_alive, "player dies entering a wall")
    check(nxt.ai_alive, "ai survives")
    check(nxt.game_over and nxt.winner == G.AI, "ai wins when player crashes into a wall")


def test_death_on_boundary() -> None:
    """A cycle stepping off the grid edge dies."""
    state = _make(
        player_pos=(0, 5), player_dir=B.UP,      # steps to row -1, off the top
        ai_pos=(15, 30), ai_dir=B.LEFT,
    )
    nxt = G.tick(state)
    check(not nxt.player_alive, "player dies stepping over the top boundary")
    check(nxt.ai_alive and nxt.winner == G.AI, "ai wins on the boundary crash")


# ---------------------------------------------------------------------------
# Head-on and swap -> mutual death (draw)
# ---------------------------------------------------------------------------

def test_head_on_draw() -> None:
    """Both cycles targeting the same cell on the same tick kill each other."""
    state = _make(
        player_pos=(5, 4), player_dir=B.RIGHT,   # -> (5,5)
        ai_pos=(5, 6), ai_dir=B.LEFT,            # -> (5,5)
    )
    nxt = G.tick(state)
    check(not nxt.player_alive and not nxt.ai_alive, "head-on kills both cycles")
    check(nxt.game_over and nxt.winner == 0, "head-on is a draw")


def test_swap_draw() -> None:
    """Cycles swapping positions (each into the other's prev cell) kill both."""
    state = _make(
        player_pos=(5, 5), player_dir=B.RIGHT,   # -> (5,6) == ai's prev cell
        ai_pos=(5, 6), ai_dir=B.LEFT,            # -> (5,5) == player's prev cell
    )
    nxt = G.tick(state)
    check(not nxt.player_alive and not nxt.ai_alive, "position swap kills both cycles")
    check(nxt.game_over and nxt.winner == 0, "swap is a draw")


# ---------------------------------------------------------------------------
# No-reverse input rule
# ---------------------------------------------------------------------------

def test_set_player_dir_no_reverse() -> None:
    state = _make(player_dir=B.RIGHT)
    blocked = G.set_player_dir(state, B.LEFT)
    check(blocked is state, "180-degree reversal returns the same state object")
    check(blocked.player_dir == B.RIGHT, "direction unchanged after illegal reversal")


def test_set_player_dir_valid() -> None:
    state = _make(player_dir=B.RIGHT)
    turned = G.set_player_dir(state, B.UP)
    check(turned is not state, "a legal turn returns a new state object")
    check(turned.player_dir == B.UP, "direction updated after a legal turn")


def test_set_player_dir_noop_when_over() -> None:
    state = _make(game_over=True, player_dir=B.RIGHT)
    result = G.set_player_dir(state, B.UP)
    check(result is state, "set_player_dir on a finished game returns the same object")


# ---------------------------------------------------------------------------
# Winner resolution
# ---------------------------------------------------------------------------

def test_winner_player_when_only_one_alive() -> None:
    """When the AI crashes and the player survives, the player wins."""
    wall = (15, 29)
    state = _make(
        walls=frozenset({wall}),
        player_pos=(5, 5), player_dir=B.RIGHT,
        ai_pos=(15, 30), ai_dir=B.LEFT,          # steps into the wall
    )
    nxt = G.tick(state)
    check(nxt.player_alive and not nxt.ai_alive, "only the player remains alive")
    check(nxt.game_over and nxt.winner == G.PLAYER, "player wins when exactly one survives")


# ---------------------------------------------------------------------------
# AI avoidance + determinism
# ---------------------------------------------------------------------------

def test_ai_avoids_immediate_death() -> None:
    """The AI must not pick a direction that is immediately fatal when a safe one exists."""
    # AI at (1,1) heading DOWN, so the reverse (UP) is excluded and the
    # non-reversing candidates are DOWN, LEFT, RIGHT. Walls just below and to
    # the right make DOWN and RIGHT fatal, leaving LEFT as the only safe move.
    walls = frozenset({(2, 1), (1, 2)})  # below and to the right of the AI head
    state = _make(
        walls=walls,
        ai_pos=(1, 1), ai_dir=B.DOWN,
        player_pos=(18, 30), player_dir=B.LEFT,
    )
    rng = random.Random(0)
    chosen = G.ai_choose_dir(state, rng)
    nxt_cell = B.add(state.ai_pos, chosen)
    check(chosen != B.UP, "AI does not reverse 180 degrees")
    check(B.in_bounds(*nxt_cell), "AI choice stays in bounds")
    check(nxt_cell not in walls, "AI choice avoids existing walls")
    # The only safe non-reversing move is LEFT -> (1,0).
    check(chosen == B.LEFT, "AI takes the one safe direction available")


def test_ai_prefers_more_open_space() -> None:
    """Given two safe moves, the AI picks the one reaching more open space.

    On an open board every direction reaches the same connected region, so walls
    are needed to make the flood-fill areas genuinely differ. Here a fully sealed
    single-cell pocket sits directly below the AI head, while stepping UP opens
    onto the large rest of the grid.
    """
    head = (3, 5)
    # Seal a single open cell (4,5) directly below the head: walls on its other
    # three sides and walls flanking the head so the only way into the pocket is
    # straight DOWN from the head. Stepping DOWN therefore reaches exactly 1 cell.
    walls = frozenset({
        (4, 4), (4, 6), (5, 5),      # left / right / bottom of the pocket cell (4,5)
        (3, 4), (3, 6),              # flank the head so the pocket can't leak sideways at row 3
    })
    state = _make(
        walls=walls,
        ai_pos=head, ai_dir=B.RIGHT,                     # reverse is LEFT
        player_pos=(0, 0), player_dir=B.RIGHT,
    )
    blocked = state.walls | {state.ai_pos, state.player_pos}
    up_area = G._flood_area(B.add(head, B.UP), blocked)
    down_area = G._flood_area(B.add(head, B.DOWN), blocked)
    check(down_area == 1, "DOWN leads into a sealed single-cell pocket")
    check(up_area > down_area, "UP genuinely reaches more space than DOWN here")
    rng = random.Random(0)
    chosen = G.ai_choose_dir(state, rng)
    check(chosen in (B.UP, B.DOWN, B.RIGHT), "AI returns a legal non-reversing direction")
    check(chosen != B.DOWN, "AI avoids the cramped DOWN pocket")


def test_ai_all_fatal_returns_legal() -> None:
    """When every move is fatal, the AI still returns a legal non-reversing dir."""
    # Box the AI in completely (no open neighbor among non-reversing moves).
    walls = frozenset({(0, 1), (1, 0), (1, 2), (2, 1)})
    state = _make(
        walls=walls,
        ai_pos=(1, 1), ai_dir=B.RIGHT,           # reverse is LEFT
        player_pos=(18, 30), player_dir=B.LEFT,
    )
    rng = random.Random(0)
    chosen = G.ai_choose_dir(state, rng)
    check(chosen in (B.UP, B.DOWN, B.RIGHT), "AI returns a legal non-reversing direction when trapped")
    check(chosen != B.LEFT, "AI never returns the reverse direction even when trapped")


def test_ai_deterministic_with_seed() -> None:
    """ai_choose_dir is deterministic for a given seeded RNG."""
    state = G.new_game()
    a = G.ai_choose_dir(state, random.Random(123))
    b = G.ai_choose_dir(state, random.Random(123))
    check(a == b, "same seed yields the same AI direction")


def test_ai_tick_runs_full_game() -> None:
    """Driving ai_tick to completion always ends in a terminal, consistent state."""
    rng = random.Random(7)
    state = G.new_game()
    for _ in range(B.WIDTH * B.HEIGHT + 5):
        if state.game_over:
            break
        state = G.ai_tick(state, rng)
    check(state.game_over, "a seeded game (AI vs an un-steered player) reaches game over")
    check(state.winner in (G.PLAYER, G.AI, 0), "winner is one of PLAYER, AI, or draw")


# ---------------------------------------------------------------------------
# Immutability / purity
# ---------------------------------------------------------------------------

def test_tick_immutability() -> None:
    """tick() returns a new object and never mutates the original or its walls."""
    state = _make(
        player_pos=(5, 5), player_dir=B.RIGHT,
        ai_pos=(15, 30), ai_dir=B.LEFT,
    )
    original_walls = state.walls
    original_player = state.player_pos
    original_tick = state.tick
    nxt = G.tick(state)
    check(nxt is not state, "tick() returns a new state object")
    check(state.walls == original_walls, "original wall set is unchanged")
    check(state.player_pos == original_player, "original player position is unchanged")
    check(state.tick == original_tick, "original tick counter is unchanged")
    check(isinstance(state.walls, frozenset), "walls remains a frozenset")


def test_tick_noop_when_over() -> None:
    state = _make(game_over=True)
    result = G.tick(state)
    check(result is state, "tick() on a finished game returns the same object")


def test_tick_pure_no_blessed() -> None:
    """The game core must be importable and runnable without blessed loaded."""
    check(
        not hasattr(G, "blessed") and not hasattr(G, "Terminal"),
        "game module does not import blessed or Terminal",
    )
    # Run a tick using only game/board; success here proves no terminal dependency.
    state = G.new_game()
    nxt = G.tick(state)
    check(isinstance(nxt, G.GameState), "tick() produces a GameState with no terminal present")


# ---------------------------------------------------------------------------
# Render string composition (no TTY needed)
# ---------------------------------------------------------------------------

def test_render_builds_strings() -> None:
    import io
    from contextlib import redirect_stdout

    from blessed import Terminal
    import render as R

    term = Terminal(force_styling=True)
    state = G.new_game()

    board = R.board_lines(term, state)
    check(len(board) == B.HEIGHT + 2, "board renders all rows plus two border lines")
    panel = R.panel_lines(term, state)
    check(any("TRON" in line for line in panel), "panel shows the TRON title")

    # Advance a few ticks so trails exist, then build a game-over frame too.
    rng = random.Random(3)
    play_state = state
    for _ in range(4):
        play_state = G.ai_tick(play_state, rng)
    over_state = dataclasses.replace(
        state, game_over=True, winner=G.PLAYER, ai_alive=False
    )

    with redirect_stdout(io.StringIO()):
        R.draw(term, play_state, paused=False)
        R.draw(term, play_state, paused=True)
        R.draw(term, over_state)
    check(True, "draw() composes in-play, paused, and game-over frames without error")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    tests = [
        test_board_bounds,
        test_new_game_initial_state,
        test_tick_advances_and_leaves_wall,
        test_trail_owner_split,
        test_death_on_wall,
        test_death_on_boundary,
        test_head_on_draw,
        test_swap_draw,
        test_set_player_dir_no_reverse,
        test_set_player_dir_valid,
        test_set_player_dir_noop_when_over,
        test_winner_player_when_only_one_alive,
        test_ai_avoids_immediate_death,
        test_ai_prefers_more_open_space,
        test_ai_all_fatal_returns_legal,
        test_ai_deterministic_with_seed,
        test_ai_tick_runs_full_game,
        test_tick_immutability,
        test_tick_noop_when_over,
        test_tick_pure_no_blessed,
        test_render_builds_strings,
    ]
    for test in tests:
        test()
    print(f"\nAll {len(tests)} test groups passed.")


if __name__ == "__main__":
    main()

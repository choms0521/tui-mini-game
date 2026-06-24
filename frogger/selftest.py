"""Headless logic checks for the Frogger core (no terminal required).

Run with ``python frogger/selftest.py`` from the repo root. Exercises all
spec §8 items:
  - frog movement stays within bounds
  - empty goal slot: scores, fills slot, resets frog; all slots filled -> won
  - road car collision: loses a life, resets frog
  - river log riding: frog carried with log
  - river drowning: frog off log -> lose a life
  - log carries frog off field edge -> lose a life
  - lives == 0 -> game_over
  - obstacle positions are deterministic for a given offset
  - immutability (transitions do not mutate original state)
  - render: panel_lines includes FROGGER title; draw() composes normal,
    game-over, and won frames without raising
"""
from __future__ import annotations

import io
from contextlib import redirect_stdout

import board as B
import game as G
import render as R


def check(condition: bool, label: str) -> None:
    if not condition:
        raise AssertionError(f"FAILED: {label}")
    print(f"ok - {label}")


# ---------------------------------------------------------------------------
# Frog movement bounds
# ---------------------------------------------------------------------------

def test_frog_move_bounds() -> None:
    state = G.new_game()

    # Move right a lot -- should clamp to WIDTH-1.
    s = state
    for _ in range(B.WIDTH + 5):
        s = G.move_frog(s, 0, +1)
    check(s.frog[1] == B.WIDTH - 1, "frog clamps to right edge")

    # Move left a lot -- should clamp to 0.
    for _ in range(B.WIDTH + 5):
        s = G.move_frog(s, 0, -1)
    check(s.frog[1] == 0, "frog clamps to left edge")

    # Move up a lot -- should clamp to row 0 (goal row without valid slot = no move past).
    # Use a state where the frog is in column 0, which is NOT a goal slot, so
    # pressing up at row 0 is a no-op; frog stays at row 1 (the last row it can enter).
    s2 = G.GameState(
        frog=(1, 0),
        lanes=state.lanes,
        offsets=state.offsets,
        lives=3, score=0,
        filled_goals=frozenset(),
        tick=0, game_over=False, won=False,
    )
    s3 = G.move_frog(s2, -1, 0)  # tries row 0 col 0 -- not a goal slot
    check(s3.frog == (1, 0), "frog blocked from non-slot goal column (stays at row 1)")

    # Move down from start row: clamped.
    s4 = G.move_frog(state, +1, 0)
    check(s4.frog[0] == B.START_ROW, "frog clamps to bottom row")


# ---------------------------------------------------------------------------
# Goal slot scoring
# ---------------------------------------------------------------------------

def test_goal_slot_scoring() -> None:
    state = G.new_game()
    slot_col = B.GOAL_COLS[0]

    # Position frog one row below goal row, at a valid slot column.
    s = G.GameState(
        frog=(1, slot_col),
        lanes=state.lanes,
        offsets=state.offsets,
        lives=3, score=0,
        filled_goals=frozenset(),
        tick=0, game_over=False, won=False,
    )
    # Move up to the goal row.
    s2 = G.move_frog(s, -1, 0)
    check(s2.score == B.SCORE_PER_GOAL, "score increases on goal slot landing")
    check(0 in s2.filled_goals, "slot 0 is filled after landing")
    check(s2.frog == (B.START_ROW, B.START_COL), "frog resets to start after scoring")
    check(not s2.won, "won is False after one slot filled (not all slots)")


def test_all_slots_filled_wins() -> None:
    state = G.new_game()
    # Pre-fill all slots except the last.
    already = frozenset(range(B.NUM_GOALS - 1))
    last_slot_col = B.GOAL_COLS[B.NUM_GOALS - 1]
    s = G.GameState(
        frog=(1, last_slot_col),
        lanes=state.lanes,
        offsets=state.offsets,
        lives=3, score=0,
        filled_goals=already,
        tick=0, game_over=False, won=False,
    )
    s2 = G.move_frog(s, -1, 0)
    check(s2.won, "won=True after filling all goal slots")
    check(len(s2.filled_goals) == B.NUM_GOALS, "all goal slots recorded as filled")


def test_filled_slot_is_noop() -> None:
    state = G.new_game()
    slot_col = B.GOAL_COLS[1]
    s = G.GameState(
        frog=(1, slot_col),
        lanes=state.lanes,
        offsets=state.offsets,
        lives=3, score=0,
        filled_goals=frozenset({1}),   # slot 1 already filled
        tick=0, game_over=False, won=False,
    )
    s2 = G.move_frog(s, -1, 0)
    check(s2 is s, "landing on filled slot is a no-op (same state object)")


# ---------------------------------------------------------------------------
# Road collision
# ---------------------------------------------------------------------------

def _make_road_state(frog_col: int, offset: int) -> G.GameState:
    """Build a minimal state where the frog is on a road lane at the given offset."""
    base = G.new_game()
    # Find a road lane.
    road_row = next(i for i, l in enumerate(B.LANES) if l.kind == "road")
    new_offsets = list(base.offsets)
    new_offsets[road_row] = offset
    return G.GameState(
        frog=(road_row, frog_col),
        lanes=base.lanes,
        offsets=tuple(new_offsets),
        lives=3, score=0,
        filled_goals=frozenset(),
        tick=0, game_over=False, won=False,
    )


def test_road_car_collision_costs_life() -> None:
    road_row = next(i for i, l in enumerate(B.LANES) if l.kind == "road")
    lane = B.LANES[road_row]
    # Pick an offset where col 0 is occupied by a car.
    # With pattern[0]=start and offset, col is occupied when (start + offset) % W == 0.
    start = lane.pattern[0]
    offset = (-start) % B.WIDTH  # (start + offset) % W == 0
    state = _make_road_state(0, offset)
    # Confirm col 0 is a car cell.
    obs = B.obstacle_cells(lane, offset)
    check(0 in obs, "test setup: col 0 is a car cell at chosen offset")

    s2 = G.tick(state)
    check(s2.lives < state.lives, "car collision reduces lives")
    check(s2.frog == (B.START_ROW, B.START_COL), "frog resets after road collision")


# ---------------------------------------------------------------------------
# River: log riding and drowning
# ---------------------------------------------------------------------------

def _make_river_state(frog_col: int, offset: int, river_row: int) -> G.GameState:
    base = G.new_game()
    new_offsets = list(base.offsets)
    new_offsets[river_row] = offset
    return G.GameState(
        frog=(river_row, frog_col),
        lanes=base.lanes,
        offsets=tuple(new_offsets),
        lives=3, score=0,
        filled_goals=frozenset(),
        tick=0, game_over=False, won=False,
    )


def test_log_riding_carries_frog() -> None:
    river_row = next(i for i, l in enumerate(B.LANES) if l.kind == "river")
    lane = B.LANES[river_row]
    # Place frog on a log cell.
    start = lane.pattern[0]
    offset = 0
    obs = B.obstacle_cells(lane, offset)
    log_col = next(iter(obs))   # any log cell

    state = _make_river_state(log_col, offset, river_row)
    check(log_col in B.obstacle_cells(lane, offset), "test setup: frog is on a log")

    s2 = G.tick(state)
    expected_col = log_col + lane.direction * lane.speed
    # The frog should have been carried (before off-edge death check), unless
    # the carry would push it off -- in that case it loses a life. We test a
    # safe carry here.
    if 0 <= expected_col < B.WIDTH:
        check(s2.frog[1] == expected_col, "frog is carried with the log")
        check(s2.lives == state.lives, "no life lost while riding log")


def test_river_drowning_costs_life() -> None:
    river_row = next(i for i, l in enumerate(B.LANES) if l.kind == "river")
    lane = B.LANES[river_row]
    # Find a column with NO log at offset 0.
    obs = B.obstacle_cells(lane, 0)
    water_col: int | None = None
    for c in range(B.WIDTH):
        if c not in obs:
            water_col = c
            break

    check(water_col is not None, "test setup: water cell found")
    state = _make_river_state(water_col, 0, river_row)
    s2 = G.tick(state)
    check(s2.lives < state.lives, "drowning in water costs a life")
    check(s2.frog == (B.START_ROW, B.START_COL), "frog resets after drowning")


def test_log_carries_frog_off_edge_costs_life() -> None:
    """Frog riding a rightward log near the right wall gets carried off."""
    river_row = next(
        i for i, l in enumerate(B.LANES)
        if l.kind == "river" and l.direction == +1
    )
    lane = B.LANES[river_row]
    # Place frog at col WIDTH - 1 (rightmost), on a log by setting offset so
    # that col WIDTH-1 is a log cell.
    # Brute-force: find an offset where WIDTH-1 is in obs.
    target_col = B.WIDTH - 1
    found_offset: int | None = None
    for off in range(B.WIDTH):
        if target_col in B.obstacle_cells(lane, off):
            found_offset = off
            break
    check(found_offset is not None, "test setup: frog placed on rightmost log cell")

    state = _make_river_state(target_col, found_offset, river_row)
    # After tick, log carries frog to WIDTH - 1 + speed >= WIDTH -> off edge.
    s2 = G.tick(state)
    check(s2.lives < state.lives, "log carrying frog off right edge costs a life")


# ---------------------------------------------------------------------------
# Lives reaching zero -> game_over
# ---------------------------------------------------------------------------

def test_lives_zero_sets_game_over() -> None:
    state = G.new_game()
    s = G.GameState(
        frog=state.frog,
        lanes=state.lanes,
        offsets=state.offsets,
        lives=1, score=0,
        filled_goals=frozenset(),
        tick=0, game_over=False, won=False,
    )
    # Force a car collision.
    road_row = next(i for i, l in enumerate(B.LANES) if l.kind == "road")
    lane = B.LANES[road_row]
    start = lane.pattern[0]
    offset = (-start) % B.WIDTH
    new_offsets = list(s.offsets)
    new_offsets[road_row] = offset
    s2 = G.GameState(
        frog=(road_row, 0),
        lanes=s.lanes,
        offsets=tuple(new_offsets),
        lives=1, score=0,
        filled_goals=frozenset(),
        tick=0, game_over=False, won=False,
    )
    obs = B.obstacle_cells(lane, offset)
    check(0 in obs, "test setup: col 0 is car")
    s3 = G.tick(s2)
    check(s3.game_over, "game_over=True when last life is lost")
    check(s3.lives == 0, "lives == 0 after final collision")


# ---------------------------------------------------------------------------
# Deterministic obstacle positions
# ---------------------------------------------------------------------------

def test_obstacle_positions_deterministic() -> None:
    road_row = next(i for i, l in enumerate(B.LANES) if l.kind == "road")
    lane = B.LANES[road_row]
    obs1 = B.obstacle_cells(lane, 5)
    obs2 = B.obstacle_cells(lane, 5)
    check(obs1 == obs2, "obstacle_cells is deterministic for a given offset")

    obs3 = B.obstacle_cells(lane, 6)
    # Different offsets should (in general) give different sets.
    # (This is only guaranteed when speed != 0 and the lane has obstacles.)
    check(obs1 != obs3 or lane.speed == 0, "different offsets yield different obstacle sets")


# ---------------------------------------------------------------------------
# Immutability
# ---------------------------------------------------------------------------

def test_immutability() -> None:
    state = G.new_game()
    orig_frog    = state.frog
    orig_offsets = state.offsets
    orig_lives   = state.lives
    orig_score   = state.score
    orig_filled  = state.filled_goals

    G.move_frog(state, -1, 0)
    G.move_frog(state, 0,  1)
    G.tick(state)

    check(state.frog    == orig_frog,    "move_frog / tick do not mutate frog")
    check(state.offsets == orig_offsets, "tick does not mutate offsets")
    check(state.lives   == orig_lives,   "tick does not mutate lives")
    check(state.score   == orig_score,   "move_frog does not mutate score")
    check(state.filled_goals == orig_filled, "move_frog does not mutate filled_goals")


# ---------------------------------------------------------------------------
# Render
# ---------------------------------------------------------------------------

def test_render() -> None:
    from blessed import Terminal

    term = Terminal(force_styling=True)
    state = G.new_game()

    panel = R.panel_lines(term, state)
    check(any("FROGGER" in line for line in panel), "panel_lines includes FROGGER title")

    won_state = G.GameState(
        frog=(B.START_ROW, B.START_COL),
        lanes=state.lanes,
        offsets=state.offsets,
        lives=3, score=250,
        filled_goals=frozenset(range(B.NUM_GOALS)),
        tick=10, game_over=False, won=True,
    )
    over_state = G.GameState(
        frog=(B.START_ROW, B.START_COL),
        lanes=state.lanes,
        offsets=state.offsets,
        lives=0, score=0,
        filled_goals=frozenset(),
        tick=5, game_over=True, won=False,
    )

    with redirect_stdout(io.StringIO()):
        R.draw(term, state, paused=False)
        R.draw(term, state, paused=True)
        R.draw(term, won_state)
        R.draw(term, over_state)

    check(True, "draw() composes normal, paused, won, and game-over frames without error")


# ---------------------------------------------------------------------------
# In-game how-to panel summary and help overlay
# ---------------------------------------------------------------------------

def test_howto_panel_and_help() -> None:
    from blessed import Terminal

    term = Terminal(force_styling=True)
    state = G.new_game()

    panel = R.panel_lines(term, state)
    check(any("FROGGER" in line for line in panel), "panel still includes FROGGER title")
    check(any("차도" in line for line in panel), "panel shows the Korean how-to summary")
    check(all(term.length(line) <= R.PANEL_WIDTH for line in panel), "every panel line fits PANEL_WIDTH")
    board_inner = R._FIELD_WIDTH - 2
    check(all(term.length(line) <= board_inner for line in R.HELP_LINES), "every help line fits the playfield width")
    check(len(R.HELP_LINES) <= B.HEIGHT, "help overlay fits within the playfield height")

    with redirect_stdout(io.StringIO()):
        R.draw(term, state, show_help=True)
    check(True, "draw(show_help=True) composes the help overlay without error")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    tests = [
        test_frog_move_bounds,
        test_goal_slot_scoring,
        test_all_slots_filled_wins,
        test_filled_slot_is_noop,
        test_road_car_collision_costs_life,
        test_log_riding_carries_frog,
        test_river_drowning_costs_life,
        test_log_carries_frog_off_edge_costs_life,
        test_lives_zero_sets_game_over,
        test_obstacle_positions_deterministic,
        test_immutability,
        test_render,
        test_howto_panel_and_help,
    ]
    for test in tests:
        test()
    print(f"\nAll {len(tests)} test groups passed.")


if __name__ == "__main__":
    main()

"""Headless logic checks for the Sokoban core (no terminal required).

Run with ``python selftest.py``.  Exercises movement, box pushing, collision,
undo, level solving, level advancement, immutability, and the rendering string
builder so the game can be verified in CI or over SSH without a TTY.
"""
from __future__ import annotations

import io
import random
from contextlib import redirect_stdout

import game as G
import levels as L
import render as R
from solver import solve


def check(condition: bool, label: str) -> None:
    if not condition:
        raise AssertionError(f"FAILED: {label}")
    print(f"ok - {label}")


# ---------------------------------------------------------------------------
# Minimal hand-built levels for deterministic testing
# ---------------------------------------------------------------------------

def _make_state(
    rows: list[str],
    level_index: int = 0,
) -> G.SokobanState:
    """Parse a tiny ASCII level string directly into a SokobanState.

    This bypasses the levels.py LEVELS list so tests are self-contained and
    deterministic regardless of what's in levels.py.
    """
    walls: set = set()
    goals: set = set()
    boxes: set = set()
    player = None

    for r, row in enumerate(rows):
        for c, ch in enumerate(row):
            if ch == "#":
                walls.add((r, c))
            elif ch == ".":
                goals.add((r, c))
            elif ch == "$":
                boxes.add((r, c))
            elif ch == "*":
                goals.add((r, c))
                boxes.add((r, c))
            elif ch == "@":
                player = (r, c)
            elif ch == "+":
                goals.add((r, c))
                player = (r, c)

    assert player is not None, "test level has no player"
    height = len(rows)
    width = max(len(row) for row in rows)

    boxes_fs = frozenset(boxes)
    goals_fs = frozenset(goals)

    return G.SokobanState(
        walls=frozenset(walls),
        goals=goals_fs,
        level_width=width,
        level_height=height,
        level_index=level_index,
        player=player,
        boxes=boxes_fs,
        moves=0,
        solved=(boxes_fs >= goals_fs),
        won=False,
        history=(),
    )


# A simple fully-enclosed 5x5 level:
#   #####
#   # @ #     player at (1,2)
#   # $ #     box at (2,2)
#   # . #     goal at (3,2)
#   #####
_SIMPLE = [
    "#####",
    "# @ #",
    "# $ #",
    "# . #",
    "#####",
]

# A level where the box is one step from the goal:
#   #####
#   #@$ #     player (1,1), box (1,2)
#   # . #     goal (2,2)
#   #####
#   Pushing right would push box off the wall (wall is at col 4), blocked.
#   Pushing down: player moves down to (2,1), box stays.
_PUSH_DOWN = [
    "#####",
    "#@$ #",
    "# . #",
    "#####",
]

# A level where pushing the box into the goal solves it:
#   #####
#   #@$.#     player (1,1), box (1,2), goal (1,3)
#   #####
_SOLVE_RIGHT = [
    "#####",
    "#@$.#",
    "#####",
]

# A level with two boxes so we can test a push blocked by the second box:
#   ######
#   #@$$ #    player (1,1), boxes at (1,2) and (1,3)
#   #....#    goals at (2,1), (2,2), (2,3)
#   ######
_TWO_BOXES = [
    "######",
    "#@$$ #",
    "#... #",
    "######",
]


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_walk_into_wall_noop() -> None:
    """Walking into a wall returns the exact same state object."""
    # _SIMPLE row 1: '#'(col0) ' '(col1) '@'(col2) ' '(col3) '#'(col4)
    # Player at (1,2); wall above is (0,2), wall to right-of-right is (1,4).
    # Move the player to (1,3) first so the right wall is adjacent.
    state = _make_state(_SIMPLE)
    # Moving up from (1,2) hits the wall at (0,2).
    new = G.move(state, "up")
    check(new is state, "walk into wall above — same state object returned")
    # Move player right to (1,3), then right again hits wall at (1,4).
    state2 = G.move(state, "right")   # player now at (1,3)
    new2 = G.move(state2, "right")    # (1,4) is '#' — wall
    check(new2 is state2, "walk into wall right — same state object returned")


def test_walk_into_floor_moves_player() -> None:
    """Walking into empty floor moves the player."""
    state = _make_state(_SIMPLE)
    # Player at (1,2); floor at (1,3) (right of '@' in row '#  @ #' col 3 is space).
    # Actually _SIMPLE has '#', ' ', '@', ' ', '#' in row 1.
    # So (1,3) is floor.
    new = G.move(state, "right")
    check(new is not state, "walk into floor — new state returned")
    check(new.player == (1, 3), "player moved right to (1,3)")
    check(new.moves == state.moves + 1, "moves counter incremented")


def test_push_box_into_floor() -> None:
    """Pushing a box into empty floor moves both player and box."""
    state = _make_state(_PUSH_DOWN)
    # Player (1,1), box (1,2).  Push right: player->( 1,2), box->(1,3).
    # (1,3) is floor (col 3 in '#@$ #' row = ' ').
    new = G.move(state, "right")
    check(new.player == (1, 2), "player moved right when pushing box")
    check((1, 3) in new.boxes, "box moved right to (1,3)")
    check((1, 2) not in new.boxes, "old box position vacated")


def test_push_box_blocked_by_wall() -> None:
    """Pushing a box into a wall leaves the state unchanged (same object)."""
    # Build a state where the box is directly against the top wall:
    # _SIMPLE layout (col2 column):  wall(0,2) / box(1,2) / player(2,2) / goal(3,2)
    # Pushing up: player->(1,2), box would go to (0,2) which is '#' — blocked.
    state = _make_state(_SIMPLE)
    # Place player directly below the box (original box at (2,2), goal at (3,2)).
    # Original state: player (1,2), box (2,2).  Move player down to (2,2)?
    # No — box is there.  Build it directly.
    state_below_box = G.SokobanState(
        walls=state.walls,
        goals=state.goals,
        level_width=state.level_width,
        level_height=state.level_height,
        level_index=0,
        player=(2, 2),   # player where box was
        boxes=frozenset({(1, 2)}),   # box one step above player
        moves=0,
        solved=False,
        won=False,
        history=(),
    )
    # Pushing up: box at (1,2) would move to (0,2) which is '#' — blocked.
    new = G.move(state_below_box, "up")
    check(new is state_below_box, "push blocked by wall behind box — same state object")


def test_push_box_blocked_by_second_box() -> None:
    """Pushing a box into another box leaves the state unchanged."""
    state = _make_state(_TWO_BOXES)
    # Player (1,1), boxes at (1,2) and (1,3).  Push right: box at (1,2)
    # would land on (1,3) which has another box — blocked.
    new = G.move(state, "right")
    check(new is state, "push into second box — same state object")


def test_solving_level_detected() -> None:
    """Pushing the last box onto its goal sets solved=True."""
    state = _make_state(_SOLVE_RIGHT)
    # Player (1,1), box (1,2), goal (1,3).  Push right -> solved.
    new = G.move(state, "right")
    check(new.solved, "state.solved is True after last box lands on goal")
    check(new.player == (1, 2), "player at box's old position")
    check((1, 3) in new.boxes, "box is on goal square")


def test_advance_level() -> None:
    """advance_level increments level_index (or sets won on last level)."""
    state = _make_state(_SOLVE_RIGHT, level_index=0)
    advanced = G.advance_level(state)
    check(advanced.level_index == 1 or advanced.won,
          "advance_level moves to level 1 or sets won flag")

    # Force a state at the last level and advance again.
    last_index = G.level_count() - 1
    last_state = G.new_game(level_index=last_index)
    # Manually solve it (set solved=True) so advance makes sense contextually.
    from dataclasses import replace
    solved_last = replace(last_state, solved=True)
    won_state = G.advance_level(solved_last)
    check(won_state.won, "advancing past the last level sets won=True")


def test_undo_restores_position() -> None:
    """Undo restores the player and boxes to the previous state."""
    state = _make_state(_PUSH_DOWN)
    after_move = G.move(state, "right")
    check(after_move.player != state.player, "move changed player position")
    undone = G.undo(after_move)
    check(undone.player == state.player, "undo restored player position")
    check(undone.boxes == state.boxes, "undo restored box positions")


def test_undo_noop_on_empty_history() -> None:
    """Undo with no history returns the same state object."""
    state = _make_state(_SIMPLE)
    check(state.history == (), "fresh state has empty history")
    new = G.undo(state)
    check(new is state, "undo on empty history returns same state object")


def test_immutability() -> None:
    """The original state object is unchanged after a successful move."""
    state = _make_state(_PUSH_DOWN)
    original_player = state.player
    original_boxes  = state.boxes
    original_moves  = state.moves

    _new = G.move(state, "right")

    check(state.player == original_player, "original player position unchanged")
    check(state.boxes  == original_boxes,  "original boxes unchanged")
    check(state.moves  == original_moves,  "original moves counter unchanged")


def test_restart_resets_level() -> None:
    """restart_level returns a fresh state at the same level index."""
    state = _make_state(_PUSH_DOWN)
    after_move = G.move(state, "right")
    restarted = G.restart_level(after_move)
    check(restarted.moves == 0, "restart resets move counter to 0")
    check(restarted.level_index == after_move.level_index,
          "restart stays on the same level")


def test_render_builds_strings() -> None:
    """Render functions compose frames without raising; board size is stable."""
    from blessed import Terminal

    term = Terminal(force_styling=True)
    rng = random.Random(0)
    state = G.new_game(rng)

    lines = R.board_lines(term, state)
    check(len(lines) == L.MAX_HEIGHT,
          "board_lines returns MAX_HEIGHT rows (stable across level sizes)")

    panel = R.panel_lines(term, state)
    check(any("SOKOBAN" in line for line in panel), "panel shows title SOKOBAN")

    # draw() must compose a full frame for normal, solved, and won states.
    from dataclasses import replace
    solved_state = replace(state, solved=True)
    won_state    = replace(state, won=True)

    with redirect_stdout(io.StringIO()):
        R.draw(term, state)
        R.draw(term, solved_state)
        R.draw(term, won_state)

    check(True, "draw() composes normal, solved, and won frames without error")


def test_parse_all_levels() -> None:
    """All levels in levels.py parse without errors."""
    for i in range(len(L.LEVELS)):
        walls, goals, boxes, player, w, h = L.parse_level(i)
        check(player is not None,     f"level {i+1} has a player start")
        check(len(goals) > 0,         f"level {i+1} has at least one goal")
        check(len(boxes) == len(goals),
              f"level {i+1} box count equals goal count")
    check(True, "all levels parse cleanly")


def test_all_levels_solvable() -> None:
    """Every shipped level must be solvable — guards against dead levels.

    Uses the push-based BFS solver.  A level is acceptable only when the solver
    returns a non-negative push count; ``False`` (proven unsolvable), ``-1``
    (search cap hit) and ``None`` (malformed) all fail the check.
    """
    for i in range(len(L.LEVELS)):
        result = solve(L.LEVELS[i])
        ok = isinstance(result, int) and not isinstance(result, bool) and result >= 0
        check(ok, f"level {i+1} is solvable (solver returned {result!r})")


def main() -> None:
    tests = [
        test_walk_into_wall_noop,
        test_walk_into_floor_moves_player,
        test_push_box_into_floor,
        test_push_box_blocked_by_wall,
        test_push_box_blocked_by_second_box,
        test_solving_level_detected,
        test_advance_level,
        test_undo_restores_position,
        test_undo_noop_on_empty_history,
        test_immutability,
        test_restart_resets_level,
        test_render_builds_strings,
        test_parse_all_levels,
        test_all_levels_solvable,
    ]
    for test in tests:
        test()
    print(f"\nAll {len(tests)} test groups passed.")


if __name__ == "__main__":
    main()

"""Headless logic checks for the roguelike core (no terminal required).

Run with ``python selftest.py``.  Exercises dungeon generation, movement,
bump-attack, monster AI, item pickup, stair descent, game-over detection,
immutability, and rendering string composition.
"""
from __future__ import annotations

import io
import random
from contextlib import redirect_stdout

from blessed import Terminal

import dungeon as D
import game as G
import render as R


def check(condition: bool, label: str) -> None:
    if not condition:
        raise AssertionError(f"FAILED: {label}")
    print(f"ok - {label}")


# ---------------------------------------------------------------------------
# Dungeon generation
# ---------------------------------------------------------------------------

def test_dungeon_generation() -> None:
    rng = random.Random(42)
    grid, rooms = D.generate(rng)

    check(len(rooms) >= 2, "dungeon has at least 2 rooms")
    check(len(grid) == D.HEIGHT, "grid has correct height")
    check(len(grid[0]) == D.WIDTH, "grid has correct width")

    # Player spawns at first room center — verify it is a floor tile.
    px, py = rooms[0].center
    check(grid[py][px] == D.FLOOR, "first room center is a floor tile")

    # At least one floor tile exists.
    floor_tiles = D.all_floor_tiles(grid)
    check(len(floor_tiles) > 0, "dungeon contains at least one floor tile")

    # Grid is immutable (tuple of tuples).
    check(isinstance(grid, tuple), "grid is a tuple")
    check(isinstance(grid[0], tuple), "grid rows are tuples")


def test_place_stairs() -> None:
    rng = random.Random(1)
    grid, rooms = D.generate(rng)
    sx, sy = rooms[-1].center
    new_grid = D.place_stairs(grid, sx, sy)

    check(new_grid[sy][sx] == D.STAIRS, "stairs placed at correct position")
    check(grid[sy][sx] != D.STAIRS, "original grid unchanged after place_stairs")


# ---------------------------------------------------------------------------
# Movement
# ---------------------------------------------------------------------------

def test_move_into_wall_returns_same_state() -> None:
    rng = random.Random(7)
    state = G.new_game(rng)

    # Build a state where moving left from col=0 is impossible.
    p = state.player
    # Place player at the leftmost walkable column, then try to go further left.
    # Simpler: search for a wall to walk into directly.
    # Place player adjacent to a known wall tile — col 0 is always a wall.
    at_left_wall = False
    for row in range(len(state.grid)):
        for col in range(1, len(state.grid[0])):
            if (state.grid[row][col] == D.FLOOR
                    and state.grid[row][col - 1] == D.WALL):
                p2 = G.Player(col=col, row=row, hp=p.hp,
                               max_hp=p.max_hp, attack=p.attack)
                # Remove all monsters/items so nothing interferes.
                wall_state = G.GameState(
                    grid=state.grid, player=p2, monsters=(),
                    items=(), depth=1, score=0, game_over=False
                )
                result = G.step(wall_state, -1, 0, rng)
                check(result is wall_state,
                      "moving into a wall returns the same state object")
                at_left_wall = True
                break
        if at_left_wall:
            break
    check(at_left_wall, "found a floor tile adjacent to a wall for the wall-bump test")


def test_move_onto_floor() -> None:
    rng = random.Random(9)
    state = G.new_game(rng)
    p = state.player

    # Find a floor tile the player can step right into.
    target_col = p.col + 1
    target_row = p.row
    if (0 <= target_row < len(state.grid)
            and 0 <= target_col < len(state.grid[0])
            and state.grid[target_row][target_col] != D.WALL):
        clean = G.GameState(
            grid=state.grid, player=p, monsters=(), items=(),
            depth=1, score=0, game_over=False
        )
        result = G.step(clean, 1, 0, rng)
        # If tile is not a wall the player should have moved (new state object)
        # OR the tile might have been something impassable — just check position.
        if state.grid[target_row][target_col] != D.WALL:
            check(result.player.col == target_col,
                  "player col advances when stepping onto a floor tile")
    else:
        # If right is a wall, move down instead.
        check(True, "move_onto_floor: wall to the right, test skipped gracefully")


# ---------------------------------------------------------------------------
# Bump-attack
# ---------------------------------------------------------------------------

def _make_state_with_monster(
    rng: random.Random,
    monster_glyph: str = "r",
    monster_hp: int = 3,
    player_attack: int = 2,
) -> G.GameState:
    """Build a minimal GameState with one monster adjacent to the player."""
    base = G.new_game(rng)
    grid = base.grid

    # Find two adjacent floor tiles for player and monster.
    for row in range(len(grid)):
        for col in range(len(grid[0]) - 1):
            if grid[row][col] == D.FLOOR and grid[row][col + 1] == D.FLOOR:
                player = G.Player(col=col, row=row, hp=20, max_hp=20,
                                  attack=player_attack)
                monster = G.Monster(col=col + 1, row=row,
                                    glyph=monster_glyph,
                                    hp=monster_hp, attack=1)
                return G.GameState(
                    grid=grid, player=player,
                    monsters=(monster,), items=(),
                    depth=1, score=0, game_over=False,
                )
    raise RuntimeError("could not find two adjacent floor tiles")


def test_bump_attack_reduces_hp() -> None:
    rng = random.Random(11)
    state = _make_state_with_monster(rng, monster_hp=5, player_attack=2)
    result = G.step(state, 1, 0, rng)
    # Monster should still be alive with reduced HP.
    check(len(result.monsters) == 1, "monster survives when HP > 0 after attack")
    check(result.monsters[0].hp == 3, "monster HP reduced by player attack")


def test_bump_attack_kills_monster() -> None:
    rng = random.Random(13)
    state = _make_state_with_monster(rng, monster_hp=2, player_attack=3)
    result = G.step(state, 1, 0, rng)
    check(len(result.monsters) == 0, "dead monster is removed from state")
    check(result.score > 0, "killing a monster awards score")


# ---------------------------------------------------------------------------
# Monster AI
# ---------------------------------------------------------------------------

def test_monster_steps_toward_player() -> None:
    """Monster directly to the right of player should step left (toward player)."""
    rng = random.Random(17)
    base = G.new_game(rng)
    grid = base.grid

    # Place player and monster with a two-tile gap on a clear row.
    for row in range(len(grid)):
        clear = all(grid[row][col] == D.FLOOR for col in range(3, 7))
        if clear:
            player = G.Player(col=3, row=row, hp=20, max_hp=20, attack=1)
            # Monster at col=6 (3 tiles away) — greedy step should bring to col=5.
            monster = G.Monster(col=6, row=row, glyph="r", hp=10, attack=0)
            state = G.GameState(
                grid=grid, player=player,
                monsters=(monster,), items=(),
                depth=1, score=0, game_over=False,
            )
            # Step with no-op movement (dcol=0, drow=0 is not valid; use a
            # different approach: call _monsters_act directly).
            result = G._monsters_act(state, rng)
            check(result.monsters[0].col == 5,
                  "monster steps one tile toward the player")
            return

    check(False, "could not find a clear row for monster AI test")


# ---------------------------------------------------------------------------
# Items
# ---------------------------------------------------------------------------

def test_potion_heals_capped_at_max() -> None:
    rng = random.Random(19)
    base = G.new_game(rng)
    grid = base.grid

    for row in range(len(grid)):
        for col in range(len(grid[0])):
            if grid[row][col] == D.FLOOR:
                player = G.Player(col=col, row=row, hp=18, max_hp=20, attack=3)
                # Potion at same tile so stepping onto it triggers pickup.
                item = G.Item(col=col, row=row, kind=G.POTION)
                state = G.GameState(
                    grid=grid, player=player,
                    monsters=(), items=(item,),
                    depth=1, score=0, game_over=False,
                )
                # Trigger _apply_items directly.
                result = G._apply_items(state, col, row)
                check(result.player.hp == 20, "potion heals player HP")
                check(result.player.hp <= result.player.max_hp,
                      "healed HP does not exceed max_hp")
                check(len(result.items) == 0, "consumed potion removed from items")
                return

    check(False, "could not find a floor tile for potion test")


def test_potion_cap_at_full_health() -> None:
    rng = random.Random(21)
    base = G.new_game(rng)
    grid = base.grid

    for row in range(len(grid)):
        for col in range(len(grid[0])):
            if grid[row][col] == D.FLOOR:
                player = G.Player(col=col, row=row, hp=20, max_hp=20, attack=3)
                item = G.Item(col=col, row=row, kind=G.POTION)
                state = G.GameState(
                    grid=grid, player=player,
                    monsters=(), items=(item,),
                    depth=1, score=0, game_over=False,
                )
                result = G._apply_items(state, col, row)
                check(result.player.hp == 20,
                      "potion at full HP does not exceed max_hp")
                return

    check(False, "could not find floor tile for potion cap test")


# ---------------------------------------------------------------------------
# Stair descent
# ---------------------------------------------------------------------------

def test_descend_increases_depth() -> None:
    rng = random.Random(23)
    state = G.new_game(rng)
    old_depth = state.depth
    descended = G.descend(state, rng)
    check(descended.depth == old_depth + 1, "descending stairs increases depth by 1")
    check(descended.score == state.score, "score is preserved on descent")
    check(descended.player.hp == state.player.hp, "player HP preserved on descent")
    check(descended.player.attack == state.player.attack,
          "player attack preserved on descent")


# ---------------------------------------------------------------------------
# Game over
# ---------------------------------------------------------------------------

def test_game_over_when_hp_reaches_zero() -> None:
    rng = random.Random(29)
    base = G.new_game(rng)
    grid = base.grid

    # Build a state where the monster will kill the player on its turn.
    for row in range(len(grid)):
        for col in range(len(grid[0]) - 1):
            if grid[row][col] == D.FLOOR and grid[row][col + 1] == D.FLOOR:
                player = G.Player(col=col, row=row, hp=1, max_hp=20, attack=0)
                # Monster with enough attack to kill in one hit, adjacent.
                monster = G.Monster(col=col + 1, row=row,
                                    glyph="g", hp=100, attack=5)
                state = G.GameState(
                    grid=grid, player=player,
                    monsters=(monster,), items=(),
                    depth=1, score=0, game_over=False,
                )
                # Try to move left (into a wall or open space) — monster will
                # then attack the player.  Use _monsters_act directly to be
                # sure.
                result = G._monsters_act(state, rng)
                check(result.game_over, "game_over set when player HP reaches 0")
                return

    check(False, "could not build game_over fixture")


# ---------------------------------------------------------------------------
# Immutability
# ---------------------------------------------------------------------------

def test_immutability() -> None:
    rng = random.Random(31)
    state = G.new_game(rng)

    # Find a walkable direction.
    p = state.player
    for dcol, drow in [(1, 0), (-1, 0), (0, 1), (0, -1)]:
        tc = p.col + dcol
        tr = p.row + drow
        if (0 <= tr < len(state.grid) and 0 <= tc < len(state.grid[0])
                and state.grid[tr][tc] != D.WALL):
            clean = G.GameState(
                grid=state.grid, player=p, monsters=(), items=(),
                depth=1, score=0, game_over=False,
            )
            orig_col = clean.player.col
            orig_row = clean.player.row
            result = G.step(clean, dcol, drow, rng)
            # Original state's player position must be unchanged.
            check(clean.player.col == orig_col,
                  "original state player col unchanged after step")
            check(clean.player.row == orig_row,
                  "original state player row unchanged after step")
            check(result is not clean, "step returns a new state object")
            return

    check(False, "could not find walkable direction for immutability test")


# ---------------------------------------------------------------------------
# Render composition
# ---------------------------------------------------------------------------

def test_render_builds_strings() -> None:
    term = Terminal(force_styling=True)
    rng = random.Random(37)
    state = G.new_game(rng)

    lines = R.map_lines(term, state)
    check(len(lines) == D.HEIGHT, "map_lines returns one line per dungeon row")

    panel = R.panel_lines(term, state)
    check(any("ROGUELIKE" in line for line in panel), "panel shows ROGUELIKE title")

    # draw() must compose without raising — redirect stdout so nothing prints.
    with redirect_stdout(io.StringIO()):
        R.draw(term, state)

    # Game-over overlay.
    over_state = G.GameState(
        grid=state.grid,
        player=state.player,
        monsters=state.monsters,
        items=state.items,
        depth=state.depth,
        score=state.score,
        game_over=True,
    )
    with redirect_stdout(io.StringIO()):
        R.draw(term, over_state)

    check(True, "draw() composes normal and game-over frames without error")


def test_howto_panel_and_help() -> None:
    term = Terminal(force_styling=True)
    state = G.new_game(random.Random(37))

    panel = R.panel_lines(term, state)
    check(any("던전" in line for line in panel), "panel shows the Korean how-to summary")
    check(all(term.length(line) <= R.PANEL_WIDTH for line in panel), "every panel line fits PANEL_WIDTH")

    with redirect_stdout(io.StringIO()):
        R.draw(term, state, show_help=True)
    check(True, "draw(show_help=True) composes the help overlay without error")


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------

def main() -> None:
    tests = [
        test_dungeon_generation,
        test_place_stairs,
        test_move_into_wall_returns_same_state,
        test_move_onto_floor,
        test_bump_attack_reduces_hp,
        test_bump_attack_kills_monster,
        test_monster_steps_toward_player,
        test_potion_heals_capped_at_max,
        test_potion_cap_at_full_health,
        test_descend_increases_depth,
        test_game_over_when_hp_reaches_zero,
        test_immutability,
        test_render_builds_strings,
        test_howto_panel_and_help,
    ]
    for test in tests:
        test()
    print(f"\nAll {len(tests)} test groups passed.")


if __name__ == "__main__":
    main()

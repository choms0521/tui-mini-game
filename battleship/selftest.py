"""Headless logic checks for the Battleship core (no terminal required).

Run with ``python selftest.py``. Exercises fleet placement validity, shot
resolution (hit/miss recording and the no-op re-shoot), sunk detection, the win
condition, the hunt/target AI (always legal, target-adjacent after a hit),
determinism under a seeded RNG, immutability, and render string composition, so
the game can be verified in CI or over SSH without a TTY.
"""
from __future__ import annotations

import io
import random
from contextlib import redirect_stdout
from dataclasses import replace

import board as B
import game as G
import render as R


def check(condition: bool, label: str) -> None:
    if not condition:
        raise AssertionError(f"FAILED: {label}")
    print(f"ok - {label}")


# ---------------------------------------------------------------------------
# Helpers: build a deterministic game from explicit ship layouts
# ---------------------------------------------------------------------------

def _ship(name: str, cells: list, horizontal: bool = True) -> G.Ship:
    return G.Ship(name=name, cells=frozenset(cells), horizontal=horizontal)


def _state(
    player_ships: tuple,
    ai_ships: tuple,
    player_shots: frozenset = frozenset(),
    ai_shots: frozenset = frozenset(),
    queue: tuple = (),
    turn: int = G.PLAYER,
) -> G.GameState:
    return G.GameState(
        player_ships=player_ships,
        ai_ships=ai_ships,
        player_shots=player_shots,
        ai_shots=ai_shots,
        ai_target_queue=queue,
        cursor=(0, 0),
        current_turn=turn,
        game_over=False,
        winner=None,
    )


def _all_cells(ships: tuple) -> set:
    cells: set = set()
    for ship in ships:
        cells |= ship.cells
    return cells


# ---------------------------------------------------------------------------
# Fleet placement
# ---------------------------------------------------------------------------

def test_placement_in_bounds_and_lengths() -> None:
    fleet = G._place_fleet(random.Random(1))
    check(len(fleet) == len(B.FLEET), "placement produces the full 5-ship fleet")

    expected_lengths = sorted(length for _, length in B.FLEET)
    actual_lengths = sorted(len(ship.cells) for ship in fleet)
    check(actual_lengths == expected_lengths, "ship cell counts match the standard fleet")

    check(
        all(B.in_bounds(cell) for ship in fleet for cell in ship.cells),
        "every ship cell is inside the 10x10 grid",
    )


def test_placement_no_overlap() -> None:
    fleet = G._place_fleet(random.Random(7))
    total = sum(len(ship.cells) for ship in fleet)
    union = _all_cells(fleet)
    check(len(union) == total, "no two ships overlap (cells are all distinct)")
    check(total == 17, "the standard fleet occupies 17 cells")


def test_placement_straight_lines() -> None:
    fleet = G._place_fleet(random.Random(3))
    for ship in fleet:
        rows = {r for r, _ in ship.cells}
        cols = {c for _, c in ship.cells}
        straight = len(rows) == 1 or len(cols) == 1
        check(straight, f"{ship.name} occupies a single row or column")


# ---------------------------------------------------------------------------
# Shot resolution
# ---------------------------------------------------------------------------

def test_hit_and_miss_recorded() -> None:
    ai_ships = (_ship("Destroyer", [(0, 0), (0, 1)]),)
    player_ships = (_ship("Destroyer", [(9, 9), (9, 8)]),)
    state = _state(player_ships, ai_ships)

    state = replace(state, cursor=(0, 0))
    hit = G.player_fire(state)
    check((0, 0) in hit.player_shots, "a fired cell is recorded in player_shots")
    check(G.is_hit(ai_ships, (0, 0)), "the shot at a ship cell is a hit")

    miss = G.player_fire(replace(hit, cursor=(5, 5), current_turn=G.PLAYER))
    check((5, 5) in miss.player_shots, "a missed cell is also recorded")
    check(not G.is_hit(ai_ships, (5, 5)), "the shot at open water is a miss")


def test_reshoot_is_noop() -> None:
    ai_ships = (_ship("Destroyer", [(0, 0), (0, 1)]),)
    player_ships = (_ship("Destroyer", [(9, 9), (9, 8)]),)
    state = _state(player_ships, ai_ships, player_shots=frozenset({(0, 0)}))

    state = replace(state, cursor=(0, 0))
    same = G.player_fire(state)
    check(same is state, "firing at an already-shot cell returns the same state")


def test_fire_blocked_when_not_player_turn() -> None:
    ai_ships = (_ship("Destroyer", [(0, 0), (0, 1)]),)
    player_ships = (_ship("Destroyer", [(9, 9), (9, 8)]),)
    state = replace(_state(player_ships, ai_ships, turn=G.AI), cursor=(0, 0))
    check(G.player_fire(state) is state,
          "player cannot fire on the AI's turn")


# ---------------------------------------------------------------------------
# Sunk and win detection
# ---------------------------------------------------------------------------

def test_sunk_detection() -> None:
    destroyer = _ship("Destroyer", [(2, 2), (2, 3)])
    check(not G.is_sunk(destroyer, frozenset({(2, 2)})),
          "a partially hit ship is not sunk")
    check(G.is_sunk(destroyer, frozenset({(2, 2), (2, 3)})),
          "a ship with all cells hit is sunk")


def test_win_when_all_enemy_ships_sunk() -> None:
    ai_ships = (_ship("Destroyer", [(0, 0), (0, 1)]),)
    player_ships = (_ship("Destroyer", [(9, 9), (9, 8)]),)
    state = _state(player_ships, ai_ships, player_shots=frozenset({(0, 0)}))

    state = replace(state, cursor=(0, 1))
    won = G.player_fire(state)
    check(won.game_over, "sinking the last enemy ship ends the game")
    check(won.winner == G.PLAYER, "the player is the winner after sinking the fleet")


def test_ai_win_when_all_player_ships_sunk() -> None:
    player_ships = (_ship("Destroyer", [(0, 0), (0, 1)]),)
    ai_ships = (_ship("Destroyer", [(9, 9), (9, 8)]),)
    # AI has already hit (0,0); firing (0,1) sinks the last player ship.
    state = _state(
        player_ships, ai_ships,
        ai_shots=frozenset({(0, 0)}),
        queue=((0, 1),),
        turn=G.AI,
    )
    after = G.ai_fire(state, random.Random(0))
    check(after.game_over, "the AI sinking the last player ship ends the game")
    check(after.winner == G.AI, "the AI is the winner after sinking the player fleet")


# ---------------------------------------------------------------------------
# AI behaviour
# ---------------------------------------------------------------------------

def test_ai_returns_unshot_legal_cell() -> None:
    rng = random.Random(5)
    state = G.new_game(rng)
    state = replace(state, current_turn=G.AI)
    seen: set = set()
    cur = state
    # Fire a long sequence; every AI shot must be a fresh, in-bounds cell.
    for _ in range(40):
        if cur.game_over:
            break
        before = cur.ai_shots
        cur = replace(cur, current_turn=G.AI)
        cur = G.ai_fire(cur, rng)
        new_cells = cur.ai_shots - before
        check(len(new_cells) == 1, "each AI shot adds exactly one cell")
        cell = next(iter(new_cells))
        check(cell not in seen, "the AI never fires at an already-shot cell")
        check(B.in_bounds(cell), "the AI shot is inside the grid")
        seen.add(cell)


def test_ai_target_mode_adjacent_after_hit() -> None:
    # A single player ship the AI is about to hit; the AI starts in hunt mode
    # but with a forced first shot on the ship via a seeded search.
    player_ships = (_ship("Cruiser", [(4, 4), (4, 5), (4, 6)]),)
    ai_ships = (_ship("Destroyer", [(0, 0), (0, 1)]),)
    # Seed the AI's first shot directly onto a ship cell via the target queue.
    state = _state(
        player_ships, ai_ships,
        queue=((4, 5),),
        turn=G.AI,
    )
    after_hit = G.ai_fire(state, random.Random(0))
    check((4, 5) in after_hit.ai_shots, "the seeded AI shot lands on the ship")
    check(G.is_hit(player_ships, (4, 5)), "that shot is a confirmed hit")
    check(len(after_hit.ai_target_queue) > 0,
          "a hit enqueues follow-up target candidates")
    check(
        all(
            adj in B.neighbours((4, 5))
            for adj in after_hit.ai_target_queue
        ),
        "all queued candidates are orthogonally adjacent to the hit",
    )

    # The very next AI shot must be one of those adjacent candidates.
    next_state = replace(after_hit, current_turn=G.AI)
    after_next = G.ai_fire(next_state, random.Random(0))
    next_cell = next(iter(after_next.ai_shots - after_hit.ai_shots))
    check(next_cell in B.neighbours((4, 5)),
          "the shot right after a hit is orthogonally adjacent to that hit")


def test_ai_returns_to_hunt_after_sinking() -> None:
    # Player ship is a 2-cell destroyer; the AI has hit one cell and the queue
    # holds the rest. Firing the second cell sinks it; the surrounding queue is
    # then pruned so the AI is no longer chasing a dead ship.
    player_ships = (
        _ship("Destroyer", [(3, 3), (3, 4)]),
        _ship("Submarine", [(7, 7), (7, 8), (7, 9)]),
    )
    ai_ships = (_ship("Destroyer", [(0, 0), (0, 1)]),)
    state = _state(
        player_ships, ai_ships,
        ai_shots=frozenset({(3, 3)}),
        queue=((3, 4), (2, 3), (4, 3), (3, 2)),
        turn=G.AI,
    )
    after = G.ai_fire(state, random.Random(0))
    sunk = G.ship_at(player_ships, (3, 3))
    check(G.is_sunk(sunk, after.ai_shots), "firing the queued cell sinks the destroyer")
    check(
        not any(cell in sunk.cells for cell in after.ai_target_queue),
        "the sunk ship's cells are pruned from the target queue",
    )
    # No other ship has been hit, so every leftover candidate around the dead
    # ship is dropped and the queue empties (clean queue -> hunt mode).
    check(
        after.ai_target_queue == (),
        "with no other live hit the queue empties so the AI returns to hunt mode",
    )


def test_ai_keeps_adjacent_ship_candidates_after_sinking() -> None:
    # Two touching ships, both already hit once. Firing the queued cell sinks the
    # Destroyer; pruning must drop the candidates that only surrounded it while
    # keeping the ones bordering the still-floating Submarine's live hit, so a
    # known hit on the adjacent ship is never abandoned.
    player_ships = (
        _ship("Destroyer", [(3, 3), (3, 4)]),
        _ship("Submarine", [(4, 4), (4, 5), (4, 6)]),
    )
    ai_ships = (_ship("Destroyer", [(0, 0), (0, 1)]),)
    state = _state(
        player_ships, ai_ships,
        # (3,3) hit the Destroyer, (4,4) hit the Submarine.
        ai_shots=frozenset({(3, 3), (4, 4)}),
        # (3,4) sinks the Destroyer; (2,3) only borders it; (5,4) and (4,5)
        # border the Submarine's live hit at (4,4).
        queue=((3, 4), (2, 3), (5, 4), (4, 5)),
        turn=G.AI,
    )
    after = G.ai_fire(state, random.Random(0))

    destroyer = G.ship_at(player_ships, (3, 3))
    check(G.is_sunk(destroyer, after.ai_shots), "firing the queued cell sinks the destroyer")
    check(
        (2, 3) not in after.ai_target_queue,
        "a candidate bordering only the sunk ship is dropped",
    )
    check(
        len(after.ai_target_queue) > 0,
        "candidates around the still-floating adjacent ship are kept",
    )
    check(
        all(
            any(neighbour == (4, 4) for neighbour in B.neighbours(pos))
            for pos in after.ai_target_queue
        ),
        "every surviving candidate still borders the adjacent ship's live hit",
    )


def test_ai_deterministic_with_seed() -> None:
    a = G.new_game(random.Random(99))
    b = G.new_game(random.Random(99))
    check(
        _all_cells(a.ai_ships) == _all_cells(b.ai_ships),
        "fleet placement is deterministic for a fixed seed",
    )

    sa = replace(a, current_turn=G.AI)
    sb = replace(b, current_turn=G.AI)
    fa = G.ai_fire(sa, random.Random(123))
    fb = G.ai_fire(sb, random.Random(123))
    check(fa.ai_shots == fb.ai_shots, "the AI's choice is deterministic for a fixed seed")


# ---------------------------------------------------------------------------
# Immutability
# ---------------------------------------------------------------------------

def test_immutability() -> None:
    ai_ships = (_ship("Destroyer", [(0, 0), (0, 1)]),)
    player_ships = (_ship("Destroyer", [(9, 9), (9, 8)]),)
    state = _state(player_ships, ai_ships)
    original_player_shots = state.player_shots
    original_cursor = state.cursor

    fired = G.player_fire(replace(state, cursor=(0, 0)))
    check(state.player_shots is original_player_shots,
          "player_fire does not mutate the original player_shots")
    check(fired is not state, "player_fire returns a new state object")

    ai_state = _state(player_ships, ai_ships, turn=G.AI)
    original_ai_shots = ai_state.ai_shots
    _ = G.ai_fire(ai_state, random.Random(0))
    check(ai_state.ai_shots is original_ai_shots,
          "ai_fire does not mutate the original ai_shots")

    _ = G.move_cursor(state, 1, 1)
    check(state.cursor == original_cursor, "move_cursor does not mutate the original cursor")


def test_move_cursor_clamps() -> None:
    ai_ships = (_ship("Destroyer", [(0, 0), (0, 1)]),)
    player_ships = (_ship("Destroyer", [(9, 9), (9, 8)]),)
    state = _state(player_ships, ai_ships)
    check(G.move_cursor(state, -1, 0) is state, "moving up from the top row is a no-op")
    check(G.move_cursor(state, 0, -1) is state, "moving left from the left column is a no-op")
    br = replace(state, cursor=(B.ROWS - 1, B.COLS - 1))
    check(G.move_cursor(br, 1, 0) is br, "moving down from the bottom row is a no-op")


# ---------------------------------------------------------------------------
# Render string composition (no TTY needed)
# ---------------------------------------------------------------------------

def test_render_builds_strings() -> None:
    from blessed import Terminal

    term = Terminal(force_styling=True)
    state = G.new_game(random.Random(2))

    blines = R.board_lines(term, state)
    # Title row + 11 rows per board (header + 10 grid rows).
    check(len(blines) == 1 + (B.ROWS + 1), "board_lines returns the title row plus both boards")

    panel = R.panel_lines(term, state)
    check(any("BATTLESHIP" in line for line in panel), "panel_lines includes the title")

    over = replace(
        state,
        game_over=True,
        winner=G.PLAYER,
        player_shots=_all_cells(state.ai_ships),
    )
    with redirect_stdout(io.StringIO()):
        R.draw(term, state)
        R.draw(term, over)
    check(True, "draw() composes in-play and game-over frames without error")


def main() -> None:
    tests = [
        test_placement_in_bounds_and_lengths,
        test_placement_no_overlap,
        test_placement_straight_lines,
        test_hit_and_miss_recorded,
        test_reshoot_is_noop,
        test_fire_blocked_when_not_player_turn,
        test_sunk_detection,
        test_win_when_all_enemy_ships_sunk,
        test_ai_win_when_all_player_ships_sunk,
        test_ai_returns_unshot_legal_cell,
        test_ai_target_mode_adjacent_after_hit,
        test_ai_returns_to_hunt_after_sinking,
        test_ai_keeps_adjacent_ship_candidates_after_sinking,
        test_ai_deterministic_with_seed,
        test_immutability,
        test_move_cursor_clamps,
        test_render_builds_strings,
    ]
    for test in tests:
        test()
    print(f"\nAll {len(tests)} test groups passed.")


if __name__ == "__main__":
    main()

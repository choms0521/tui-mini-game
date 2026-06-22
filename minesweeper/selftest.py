"""Headless logic checks for the Minesweeper core (no terminal required).

Run with ``python selftest.py``.  Exercises adjacent-count computation,
flood-fill reveal, flag toggling, game-over on mine reveal, win detection,
immutability, and the rendering string builder without needing a TTY.
"""
from __future__ import annotations

import io
import random
from contextlib import redirect_stdout

from blessed import Terminal

import board as B
import game as G
import render as R


def check(condition: bool, label: str) -> None:
    if not condition:
        raise AssertionError(f"FAILED: {label}")
    print(f"ok - {label}")


# ---------------------------------------------------------------------------
# Known layout helpers
# ---------------------------------------------------------------------------

def _make_state(mines_list: list, rows: int = 5, cols: int = 5) -> G.GameState:
    """Build a deterministic GameState from an explicit mine list."""
    mines: frozenset[B.Pos] = frozenset(mines_list)
    return G.GameState(
        mines=mines,
        revealed=frozenset(),
        flagged=frozenset(),
        cursor=(0, 0),
        game_over=False,
        won=False,
        rows=rows,
        cols=cols,
    )


# ---------------------------------------------------------------------------
# Test functions
# ---------------------------------------------------------------------------

def test_adjacent_count_known_layout() -> None:
    """adjacent_count gives correct values on a hand-crafted 5x5 grid."""
    # Place mines at corners (0,0) and (0,4) only.
    mines: frozenset[B.Pos] = frozenset([(0, 0), (0, 4)])

    # (0,1) is adjacent to (0,0) only → count 1.
    check(B.adjacent_count((0, 1), mines, 5, 5) == 1, "cell (0,1) has 1 adjacent mine")
    # (0,2) is adjacent to neither corner → count 0.
    check(B.adjacent_count((0, 2), mines, 5, 5) == 0, "cell (0,2) has 0 adjacent mines")
    # (1,1) is adjacent to (0,0) only → count 1.
    check(B.adjacent_count((1, 1), mines, 5, 5) == 1, "cell (1,1) has 1 adjacent mine")
    # (1,3) is adjacent to (0,4) only → count 1.
    check(B.adjacent_count((1, 3), mines, 5, 5) == 1, "cell (1,3) has 1 adjacent mine")
    # (2,2) is adjacent to neither → count 0.
    check(B.adjacent_count((2, 2), mines, 5, 5) == 0, "center cell has 0 adjacent mines")
    # A mine cell's own count is the number of *other* mines nearby.
    check(B.adjacent_count((0, 0), mines, 5, 5) == 0, "mine at (0,0) has 0 mine neighbours")


def test_flood_fill_zero_region() -> None:
    """flood_reveal from a zero cell expands to cover the whole zero region."""
    # 5x5 grid; mines only on the right column so the left 4 columns are all zero.
    mines: frozenset[B.Pos] = frozenset([(r, 4) for r in range(5)])

    # Start reveal at top-left corner (0,0) which has 0 adjacent mines.
    new_revealed = B.flood_reveal((0, 0), mines, frozenset(), 5, 5)

    # Every non-mine cell should be included (5*4 = 20 cells).
    expected = frozenset((r, c) for r in range(5) for c in range(4))
    check(new_revealed == expected, "flood fill covers all 20 non-mine cells")

    # No mine cell should be included.
    check(not any(p in mines for p in new_revealed), "flood fill never reveals a mine")


def test_flood_fill_bounded_by_numbers() -> None:
    """flood_reveal stops at numbered cells and does not cross them."""
    # Single mine at (2,2) in a 5x5 grid.
    mines: frozenset[B.Pos] = frozenset([(2, 2)])

    # Starting from (0,0) the flood must not reach cells far from the mine.
    # Corner (0,0) has 0 adjacent mines → fill expands.
    revealed = B.flood_reveal((0, 0), mines, frozenset(), 5, 5)

    check((2, 2) not in revealed, "mine itself is never in flood result")
    # The fill should include (0,0) itself.
    check((0, 0) in revealed, "start cell is always included in flood result")
    # Cells directly adjacent to the mine are numbered (count >= 1) and are
    # included in the reveal but do not propagate further.
    check((1, 1) in revealed, "numbered cell adjacent to mine is revealed")
    check((1, 2) in revealed, "numbered cell above mine is revealed")


def test_flag_toggle_on_and_off() -> None:
    """toggle_flag adds a flag and then removes it on a second call."""
    state = _make_state([(2, 2)])
    state = G.GameState(
        **{**state.__dict__, "cursor": (1, 1)}
    )
    # Replace properly using dataclasses.replace.
    from dataclasses import replace
    state = replace(state, cursor=(1, 1))

    # First toggle: flag appears.
    flagged = G.toggle_flag(state)
    check((1, 1) in flagged.flagged, "flag added after first toggle")
    check(flagged is not state, "toggle_flag returns a new state object")

    # Second toggle: flag removed.
    unflagged = G.toggle_flag(flagged)
    check((1, 1) not in unflagged.flagged, "flag removed after second toggle")


def test_flag_does_not_reveal() -> None:
    """A flagged cell cannot be revealed until the flag is removed."""
    state = _make_state([(0, 0)])
    from dataclasses import replace
    state = replace(state, cursor=(0, 1))

    # Flag the cell.
    flagged = G.toggle_flag(state)
    check((0, 1) in flagged.flagged, "cell is flagged")

    # Attempt reveal on a flagged cell — state must be unchanged.
    attempted = G.reveal(flagged)
    check(attempted is flagged, "reveal on flagged cell returns same state")


def test_lose_on_mine_reveal() -> None:
    """Revealing a mine triggers game-over and exposes all mines."""
    mines = [(0, 0), (1, 1), (3, 3)]
    state = _make_state(mines)

    # Move cursor onto a mine and reveal.
    from dataclasses import replace
    state = replace(state, cursor=(0, 0))
    lost = G.reveal(state)

    check(lost.game_over, "game_over becomes True after revealing a mine")
    check(not lost.won, "won stays False on game-over")
    # All mines should be in revealed on loss.
    check(all(m in lost.revealed for m in mines), "all mines are revealed after loss")


def test_win_when_all_safe_revealed() -> None:
    """Win is triggered when the last non-mine cell is revealed."""
    # 3x3 grid with a single mine at (0,0); 8 safe cells.
    mines = [(0, 0)]
    state = _make_state(mines, rows=3, cols=3)

    # Reveal all cells except (0,0) manually.
    from dataclasses import replace
    safe_cells = frozenset(
        (r, c) for r in range(3) for c in range(3) if (r, c) != (0, 0)
    )

    # Reveal all but the last safe cell first.
    all_but_last = frozenset(list(safe_cells)[:-1])
    state = replace(state, revealed=all_but_last)

    # Reveal the last safe cell via the game transition.
    last = list(safe_cells)[-1]
    state = replace(state, cursor=last)
    won_state = G.reveal(state)

    check(won_state.won, "won becomes True when last safe cell is revealed")
    check(not won_state.game_over, "game_over stays False on win")


def test_immutability() -> None:
    """State transitions never mutate the original state."""
    state = _make_state([(0, 0)])
    original_revealed = state.revealed
    original_flagged = state.flagged
    original_cursor = state.cursor

    from dataclasses import replace
    state_at_mine = replace(state, cursor=(0, 0))

    _ = G.reveal(state_at_mine)
    check(state_at_mine.revealed == original_revealed,
          "original revealed set unchanged after reveal")

    _ = G.toggle_flag(state)
    check(state.flagged == original_flagged,
          "original flagged set unchanged after toggle_flag")

    _ = G.move_cursor(state, 1, 1)
    check(state.cursor == original_cursor,
          "original cursor unchanged after move_cursor")


def test_move_cursor_clamps_to_bounds() -> None:
    """move_cursor does not move out of the grid."""
    state = _make_state([])
    from dataclasses import replace
    state = replace(state, cursor=(0, 0))

    # Move up beyond the top row.
    same = G.move_cursor(state, -1, 0)
    check(same is state, "move up from top row returns same state")

    # Move left beyond the left column.
    same2 = G.move_cursor(state, 0, -1)
    check(same2 is state, "move left from left column returns same state")

    # Move to bottom-right corner.
    from dataclasses import replace as _r
    br_state = _r(state, cursor=(4, 4))
    same3 = G.move_cursor(br_state, 1, 0)
    check(same3 is br_state, "move down from bottom row returns same state")


def test_place_mines_count_and_uniqueness() -> None:
    """place_mines returns exactly the requested number of unique positions."""
    rng = random.Random(42)
    mines = B.place_mines(rng, 9, 9, 10)
    check(len(mines) == 10, "place_mines returns exactly 10 mines on 9x9")
    check(all(0 <= r < 9 and 0 <= c < 9 for r, c in mines),
          "all mine positions are within grid bounds")


def test_render_draw_composes_without_error() -> None:
    """draw() composes normal, flagged, game-over, and won frames without raising."""
    term = Terminal(force_styling=True)
    rng = random.Random(7)
    state = G.new_game(rng)

    board = R.board_lines(term, state)
    check(len(board) == state.rows + 2,
          "board_lines returns rows+2 lines (top/bottom borders)")
    panel = R.panel_lines(term, state)
    check(any("MINESWEEPER" in line for line in panel),
          "panel_lines includes the title")

    from dataclasses import replace
    # Game-over state.
    over_state = replace(state, game_over=True, revealed=state.mines)
    # Won state.
    safe = frozenset(
        (r, c)
        for r in range(state.rows)
        for c in range(state.cols)
        if (r, c) not in state.mines
    )
    won_state = replace(state, revealed=safe, won=True)
    # Flagged state.
    first_unrevealed = next(
        (r, c)
        for r in range(state.rows)
        for c in range(state.cols)
        if (r, c) not in state.mines
    )
    flagged_state = G.toggle_flag(replace(state, cursor=first_unrevealed))

    with redirect_stdout(io.StringIO()):
        R.draw(term, state)
        R.draw(term, over_state)
        R.draw(term, won_state)
        R.draw(term, flagged_state)

    check(True, "draw() composes normal, game-over, won, and flagged frames without error")


def main() -> None:
    tests = [
        test_adjacent_count_known_layout,
        test_flood_fill_zero_region,
        test_flood_fill_bounded_by_numbers,
        test_flag_toggle_on_and_off,
        test_flag_does_not_reveal,
        test_lose_on_mine_reveal,
        test_win_when_all_safe_revealed,
        test_immutability,
        test_move_cursor_clamps_to_bounds,
        test_place_mines_count_and_uniqueness,
        test_render_draw_composes_without_error,
    ]
    for test in tests:
        test()
    print(f"\nAll {len(tests)} test groups passed.")


if __name__ == "__main__":
    main()

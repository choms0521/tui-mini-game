"""Render a :class:`game.GameState` to the terminal using blessed.

The whole frame is composed as one string and printed after moving the cursor
home, so there is no full-screen clear between frames and therefore no flicker.
Every line is padded to a fixed printable width so a shorter line never leaves
stale characters behind from the previous frame.
"""
from __future__ import annotations

from typing import List

from blessed import Terminal

import board as B
import game as G

# Layout constants (column positions, 0-based).
BOARD_X = 2
BOARD_Y = 1
PANEL_GAP = 4
PANEL_WIDTH = 20

# Each cell is rendered as " D " (3 chars wide) so digits sit centred.
_CELL_W = 3

# Truecolor RGB palette.
GIVEN_RGB = (200, 200, 210)    # fixed puzzle digits — bright, neutral
ENTRY_RGB = (90, 180, 255)     # player-entered digits — blue
CONFLICT_RGB = (255, 80, 80)   # digits that violate a constraint — red
EMPTY_RGB = (70, 70, 80)       # the dot marking a blank cell
BORDER_RGB = (120, 120, 120)   # grid lines


def _pad(term: Terminal, text: str, width: int) -> str:
    """Right-pad *text* to a fixed printable width, ignoring colour escapes."""
    extra = width - term.length(text)
    return text + " " * extra if extra > 0 else text


def _cell_str(term: Terminal, state: G.GameState, row: int, col: int,
              conflict_cells: frozenset) -> str:
    """Return the 3-character rendering of a single cell."""
    value = state.grid[row][col]
    is_cursor = (row, col) == state.cursor

    if value == B.EMPTY:
        inner = term.color_rgb(*EMPTY_RGB)(" . ")
    else:
        if (row, col) in conflict_cells:
            rgb = CONFLICT_RGB
        elif G.is_given(state, row, col):
            rgb = GIVEN_RGB
        else:
            rgb = ENTRY_RGB
        inner = term.color_rgb(*rgb)(f" {value} ")

    if is_cursor:
        return term.reverse(inner)
    return inner


def board_lines(term: Terminal, state: G.GameState) -> List[str]:
    """Return one string per board row, with 3x3 box separators and borders.

    The layout uses '+' / '-' for horizontal rules and '|' for the vertical box
    separators, drawn only on box boundaries so the three 3x3 boxes read clearly.
    """
    border = term.color_rgb(*BORDER_RGB)
    # A horizontal rule spanning all nine cells plus the four vertical bars.
    rule = border("+" + ("-" * (B.BOX * _CELL_W) + "+") * B.BOX)
    conflict_cells = B.conflicts(state.grid)

    lines: List[str] = [rule]
    for r in range(B.SIZE):
        parts = [border("|")]
        for c in range(B.SIZE):
            parts.append(_cell_str(term, state, r, c, conflict_cells))
            if (c + 1) % B.BOX == 0:
                parts.append(border("|"))
        lines.append("".join(parts))
        if (r + 1) % B.BOX == 0:
            lines.append(rule)
    return lines


def panel_lines(term: Terminal, state: G.GameState) -> List[str]:
    """Return the side-panel lines (title, stats, controls)."""
    filled = sum(1 for row in state.grid for v in row if v != B.EMPTY)
    remaining = B.SIZE * B.SIZE - filled

    lines: List[str] = [
        term.bold("SUDOKU"),
        "",
        f"Empty  {remaining:>4}",
        "",
        term.dim("arrows  move"),
        term.dim("1-9     set digit"),
        term.dim("0/bksp  clear"),
        term.dim("r       new puzzle"),
        term.dim("q       quit"),
    ]

    if state.won:
        lines.insert(0, term.bold(term.color_rgb(0, 220, 80)("SOLVED!")))
        lines.insert(1, "")

    return lines


def draw(term: Terminal, state: G.GameState) -> None:
    """Compose and print the full frame without clearing the screen."""
    board = board_lines(term, state)
    board_w = term.length(board[0]) if board else 0

    frame: List[str] = [term.home]

    for i, line in enumerate(board):
        frame.append(
            term.move_xy(BOARD_X, BOARD_Y + i) + _pad(term, line, board_w)
        )

    panel_x = BOARD_X + board_w + PANEL_GAP
    for i, line in enumerate(panel_lines(term, state)):
        frame.append(
            term.move_xy(panel_x, BOARD_Y + i) + _pad(term, line, PANEL_WIDTH)
        )

    print("".join(frame), end="", flush=True)

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
PANEL_GAP = 3
PANEL_WIDTH = 22

# Each cell is rendered as two characters so the grid looks square-ish.
_CELL_W = 2
# Total printable width of the board area: left border + cells + right border.
_BOARD_WIDTH = 1 + B.COLS * _CELL_W + 1

# Truecolor RGB for adjacent-mine numbers (classic colours).
_NUM_RGB = {
    1: (0, 0, 255),
    2: (0, 180, 0),
    3: (220, 0, 0),
    4: (0, 0, 140),
    5: (140, 0, 0),
    6: (0, 180, 180),
    7: (0, 0, 0),
    8: (128, 128, 128),
}


def _pad(term: Terminal, text: str, width: int) -> str:
    """Right-pad *text* to a fixed printable width, ignoring colour escapes."""
    extra = width - term.length(text)
    return text + " " * extra if extra > 0 else text


def _cell_str(term: Terminal, state: G.GameState, pos: B.Pos) -> str:
    """Return the two-character rendering of a single cell."""
    r, c = pos
    is_cursor = pos == state.cursor

    def _wrap(inner: str) -> str:
        if is_cursor:
            return term.reverse(inner)
        return inner

    if pos in state.revealed:
        if pos in state.mines:
            # Mine revealed (game-over explosion).
            return _wrap(term.color_rgb(255, 60, 60)(" *"))
        count = B.adjacent_count(pos, state.mines, state.rows, state.cols)
        if count == 0:
            text = term.color_rgb(50, 50, 50)("  ")
        else:
            rgb = _NUM_RGB.get(count, (200, 200, 200))
            text = term.color_rgb(*rgb)(f" {count}")
        return _wrap(text)

    if pos in state.flagged:
        return _wrap(term.color_rgb(255, 200, 0)(" F"))

    # Hidden unrevealed cell.
    hidden = term.color_rgb(100, 100, 140)("[]")
    return _wrap(hidden)


def board_lines(term: Terminal, state: G.GameState) -> List[str]:
    """Return one string per board row, including top/bottom borders."""
    border = term.color_rgb(120, 120, 120)
    top = border("+" + "-" * (state.cols * _CELL_W) + "+")
    bottom = border("+" + "-" * (state.cols * _CELL_W) + "+")

    lines = [top]
    for r in range(state.rows):
        row_parts = [border("|")]
        for c in range(state.cols):
            row_parts.append(_cell_str(term, state, (r, c)))
        row_parts.append(border("|"))
        lines.append("".join(row_parts))
    lines.append(bottom)
    return lines


def panel_lines(term: Terminal, state: G.GameState) -> List[str]:
    """Return the side-panel lines (title, stats, controls)."""
    mines_remaining = len(state.mines) - len(state.flagged)

    lines: List[str] = [
        term.bold("MINESWEEPER"),
        "",
        f"Mines  {mines_remaining:>4}",
        f"Flags  {len(state.flagged):>4}",
        "",
        term.dim("방향키  이동"),
        term.dim("space   열기"),
        term.dim("enter   열기"),
        term.dim("f       깃발"),
        term.dim("r       재시작"),
        term.dim("q       종료"),
    ]

    if state.won:
        lines.insert(0, term.bold(term.color_rgb(0, 220, 80)("YOU WIN!")))
        lines.insert(1, "")
    elif state.game_over:
        lines.insert(0, term.bold(term.color_rgb(255, 60, 60)("GAME OVER")))
        lines.insert(1, "")

    return lines


def draw(term: Terminal, state: G.GameState) -> None:
    """Compose and print the full frame without clearing the screen."""
    board_w = 1 + state.cols * _CELL_W + 1  # left border + cells + right border

    frame: List[str] = [term.home]

    for i, line in enumerate(board_lines(term, state)):
        frame.append(
            term.move_xy(BOARD_X, BOARD_Y + i) + _pad(term, line, board_w)
        )

    panel_x = BOARD_X + board_w + PANEL_GAP
    for i, line in enumerate(panel_lines(term, state)):
        frame.append(
            term.move_xy(panel_x, BOARD_Y + i) + _pad(term, line, PANEL_WIDTH)
        )

    print("".join(frame), end="", flush=True)

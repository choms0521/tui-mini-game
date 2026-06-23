"""Render a :class:`game.GameState` to the terminal using blessed.

The whole frame is composed as one string and printed after moving the cursor
home, so there is no full-screen clear between frames and therefore no flicker.
Every line is padded to a fixed printable width (via ``term.length`` like
tetris) so a shorter line never leaves stale characters from the previous
frame.
"""
from __future__ import annotations

from typing import List

from blessed import Terminal

import board as B
import game as G

# Truecolor RGB per tile value.
_TILE_RGB = {
    2:     (238, 228, 218),
    4:     (237, 224, 200),
    8:     (242, 177, 121),
    16:    (245, 149,  99),
    32:    (246, 124,  95),
    64:    (246,  94,  59),
    128:   (237, 207, 114),
    256:   (237, 204,  97),
    512:   (237, 200,  80),
    1024:  (237, 197,  63),
    2048:  (237, 194,  46),
    4096:  (60,  58, 50),
    8192:  (40,  38, 33),
}
_DEFAULT_RGB = (60, 58, 50)   # any tile above 8192

# Layout constants.
CELL_W = 6        # printable columns per cell (5 digits + 1 padding)
BOARD_X = 2
BOARD_Y = 1
PANEL_GAP = 4
PANEL_WIDTH = 20

# Derived: total printable width of the board area (4 cells + borders).
_BOARD_W = B.SIZE * CELL_W + (B.SIZE + 1)   # SIZE+1 vertical bars


def _cell_rgb(value: int):
    return _TILE_RGB.get(value, _DEFAULT_RGB)


def _render_cell(term: Terminal, value: int) -> str:
    """Return a fixed-width coloured string for one tile."""
    r, g, b = _cell_rgb(value)
    text = str(value) if value else "."
    # Centre text in CELL_W columns.
    padded = text.center(CELL_W)
    return term.color_rgb(r, g, b)(padded)


def _pad(term: Terminal, text: str, width: int) -> str:
    """Right-pad to a fixed printable width, ignoring colour escape codes."""
    extra = width - term.length(text)
    return text + " " * extra if extra > 0 else text


def board_lines(term: Terminal, state: G.GameState) -> List[str]:
    """Build one string per row of the 4x4 board, including borders."""
    border = term.color_rgb(187, 173, 160)
    sep_row = border("+" + ("-" * CELL_W + "+") * B.SIZE)

    lines = [sep_row]
    for r in range(B.SIZE):
        row_parts = [border("|")]
        for c in range(B.SIZE):
            row_parts.append(_render_cell(term, state.grid[r][c]))
            row_parts.append(border("|"))
        lines.append("".join(row_parts))
        lines.append(sep_row)
    return lines


def panel_lines(term: Terminal, state: G.GameState) -> List[str]:
    """Build the side-panel lines: title, score, and controls."""
    lines = [
        term.bold("GAME 2048"),
        "",
        "Score",
        term.bold(f"{state.score:>10}"),
        "",
        term.dim("방향키  이동"),
        term.dim("r       재시작"),
        term.dim("q       종료"),
    ]
    return lines


def _overlay(term: Terminal, text: str) -> str:
    """Return a centred, reversed-video overlay string positioned over the board."""
    # Vertically centre inside the board rows (each cell row plus separator = 2 lines each).
    y = BOARD_Y + B.SIZE + 1
    x = BOARD_X + max(0, (_BOARD_W - len(text) - 2) // 2)
    return term.move_xy(x, y) + term.reverse(term.bold(f" {text} "))


def draw(term: Terminal, state: G.GameState) -> None:
    """Compose and print a complete frame without clearing the screen."""
    frame = [term.home]

    b_lines = board_lines(term, state)
    for i, line in enumerate(b_lines):
        frame.append(term.move_xy(BOARD_X, BOARD_Y + i) + _pad(term, line, _BOARD_W))

    panel_x = BOARD_X + _BOARD_W + PANEL_GAP
    for i, line in enumerate(panel_lines(term, state)):
        frame.append(
            term.move_xy(panel_x, BOARD_Y + 1 + i) + _pad(term, line, PANEL_WIDTH)
        )

    if state.game_over:
        frame.append(_overlay(term, "GAME OVER  press r"))
    elif state.won:
        frame.append(_overlay(term, "YOU WIN!   press r or keep going"))

    print("".join(frame), end="", flush=True)

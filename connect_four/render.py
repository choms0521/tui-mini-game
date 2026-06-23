"""Render a :class:`game.GameState` to the terminal using blessed.

The whole frame is composed as one string and printed after moving the cursor
home, so there is no full-screen clear between frames and therefore no flicker.
Every line is padded to a fixed width so a shorter line never leaves stale
characters behind from the previous frame.
"""
from __future__ import annotations

from typing import List

from blessed import Terminal

import board as B
import game as G

# Layout constants
BOARD_X = 3
BOARD_Y = 2
PANEL_GAP = 4
PANEL_WIDTH = 22

# Each cell is 3 chars wide with a single space separator between columns.
_CELL_WIDTH = 3
_CELL_SEP = 1
_ROW_WIDTH = B.COLS * (_CELL_WIDTH + _CELL_SEP) - _CELL_SEP

# Truecolor per cell value.
_HUMAN_RGB = (220, 70, 70)     # red
_AI_RGB = (235, 200, 60)       # yellow
_EMPTY_RGB = (60, 60, 70)      # dim slot
_FRAME_RGB = (90, 110, 200)    # board frame tint


def _cell(term: Terminal, value: int) -> str:
    """Render one 3-char cell for a disc or an empty slot."""
    if value == G.HUMAN:
        return term.color_rgb(*_HUMAN_RGB)(" ● ")   # filled circle
    if value == G.AI:
        return term.color_rgb(*_AI_RGB)(" ● ")
    return term.color_rgb(*_EMPTY_RGB)(" · ")        # middle dot


def _pad(term: Terminal, text: str, width: int) -> str:
    """Right-pad *text* to a fixed printable width, ignoring escape codes."""
    extra = width - term.length(text)
    return text + " " * extra if extra > 0 else text


def _disc_color(term: Terminal, player: int) -> str:
    """Return a colored disc glyph for the given player."""
    rgb = _HUMAN_RGB if player == G.HUMAN else _AI_RGB
    return term.color_rgb(*rgb)("●")


def selector_line(term: Terminal, state: G.GameState, selected_col: int) -> str:
    """Render the arrow row that marks the column the human is aiming at."""
    cells: List[str] = []
    for c in range(B.COLS):
        if c == selected_col and not state.game_over:
            cells.append(" " + _disc_color(term, state.current_player) + " ")
        else:
            cells.append("   ")
    return (" " * _CELL_SEP).join(cells)


def board_lines(term: Terminal, state: G.GameState) -> List[str]:
    """Return one string per board row (ROWS rows, top to bottom)."""
    lines: List[str] = []
    for r in range(B.ROWS):
        cells = [_cell(term, state.board[r][c]) for c in range(B.COLS)]
        lines.append((" " * _CELL_SEP).join(cells))
    return lines


def panel_lines(term: Terminal, state: G.GameState) -> List[str]:
    """Return the right-side info panel as a list of strings."""
    if state.game_over:
        turn = "game over"
    elif state.current_player == G.HUMAN:
        turn = "your move"
    else:
        turn = "AI thinking"
    lines = [
        term.bold("CONNECT FOUR"),
        "",
        f"Turn   {turn}",
        f"You    {term.color_rgb(*_HUMAN_RGB)('●')} red",
        f"AI     {term.color_rgb(*_AI_RGB)('●')} yellow",
        "",
        term.dim("left/right  aim"),
        term.dim("enter/space drop"),
        term.dim("r      restart"),
        term.dim("q      quit"),
    ]
    return lines


def _overlay(term: Terminal, lines: List[str], width: int) -> str:
    """Centre each overlay line over the board's vertical midpoint."""
    y_base = BOARD_Y + B.ROWS // 2 - len(lines) // 2
    parts: List[str] = []
    for i, text in enumerate(lines):
        visible = term.length(text)
        x = BOARD_X + max(0, (width - visible) // 2)
        parts.append(term.move_xy(x, y_base + i) + text)
    return "".join(parts)


def draw(term: Terminal, state: G.GameState, selected_col: int = 0) -> None:
    """Compose and print the full frame without clearing the screen."""
    frame: List[str] = [term.home]

    # Selector arrow row above the grid.
    frame.append(term.move_xy(BOARD_X, BOARD_Y - 1) + _pad(term, selector_line(term, state, selected_col), _ROW_WIDTH))

    blines = board_lines(term, state)
    for i, line in enumerate(blines):
        frame.append(term.move_xy(BOARD_X, BOARD_Y + i) + _pad(term, line, _ROW_WIDTH))

    # Column number guide under the grid.
    guide = (" " * _CELL_SEP).join(f" {c + 1} " for c in range(B.COLS))
    frame.append(term.move_xy(BOARD_X, BOARD_Y + B.ROWS) + term.dim(_pad(term, guide, _ROW_WIDTH)))

    panel_x = BOARD_X + _ROW_WIDTH + PANEL_GAP
    for i, line in enumerate(panel_lines(term, state)):
        frame.append(term.move_xy(panel_x, BOARD_Y + i) + _pad(term, line, PANEL_WIDTH))

    if state.game_over:
        if state.winner == G.HUMAN:
            banner = term.bold(term.green(" YOU WIN! "))
        elif state.winner == G.AI:
            banner = term.bold(term.red(" AI WINS "))
        else:
            banner = term.bold(term.yellow(" DRAW "))
        frame.append(_overlay(term, [banner, term.dim(" r to retry ")], _ROW_WIDTH))

    print("".join(frame), end="", flush=True)

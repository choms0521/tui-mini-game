"""Render a :class:`game.GameState` to the terminal using blessed.

The whole frame is composed as one string and printed after moving the cursor
home, so there is no full-screen clear between frames and therefore no flicker.
Every line is padded to a fixed printable width so a shorter line never leaves
stale characters behind from the previous frame.

The board is 15x15, so each cell is kept narrow (a stone glyph plus a single
trailing space) to fit the grid and the info panel on one screen.
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
PANEL_WIDTH = 24

# Each cell is two printable characters: the glyph and a trailing separator.
_CELL_W = 2
_ROW_WIDTH = B.COLS * _CELL_W

# Truecolor per stone value.
_BLACK_RGB = (40, 40, 48)       # human (black) stone
_WHITE_RGB = (235, 235, 240)    # AI (white) stone
_GRID_RGB = (90, 90, 105)       # empty intersection marker
_LAST_RGB = (250, 180, 60)      # last-move accent ring


def _pad(term: Terminal, text: str, width: int) -> str:
    """Right-pad *text* to a fixed printable width, ignoring colour escapes."""
    extra = width - term.length(text)
    return text + " " * extra if extra > 0 else text


def _glyph(term: Terminal, value: int, is_last: bool) -> str:
    """Return the single-character glyph for a cell value."""
    if value == G.HUMAN:
        rgb = _LAST_RGB if is_last else _BLACK_RGB
        return term.color_rgb(*rgb)("●")   # filled circle
    if value == G.AI:
        rgb = _LAST_RGB if is_last else _WHITE_RGB
        return term.color_rgb(*rgb)("●")
    return term.color_rgb(*_GRID_RGB)("·")  # middle dot for empty


def _cell(term: Terminal, state: G.GameState, r: int, c: int) -> str:
    """Render one 2-char cell, highlighting the cursor with a reverse block."""
    value = state.board[r][c]
    is_last = state.last_move == (r, c)
    glyph = _glyph(term, value, is_last)
    is_cursor = (
        (r, c) == state.cursor
        and not state.game_over
        and state.current_player == G.HUMAN
    )
    if is_cursor:
        return term.reverse(glyph + " ")
    return glyph + " "


def board_lines(term: Terminal, state: G.GameState) -> List[str]:
    """Return one string per board row (ROWS rows, top to bottom)."""
    lines: List[str] = []
    for r in range(B.ROWS):
        cells = [_cell(term, state, r, c) for c in range(B.COLS)]
        lines.append("".join(cells))
    return lines


def _stone_swatch(term: Terminal, player: int) -> str:
    """Return a coloured stone glyph for the panel legend."""
    rgb = _BLACK_RGB if player == G.HUMAN else _WHITE_RGB
    return term.color_rgb(*rgb)("●")


def panel_lines(term: Terminal, state: G.GameState) -> List[str]:
    """Return the right-side info panel as a list of strings."""
    if state.game_over:
        turn = "game over"
    elif state.current_player == G.HUMAN:
        turn = "your move"
    else:
        turn = "AI thinking"

    if state.last_move is None:
        last = "-"
    else:
        lr, lc = state.last_move
        last = f"{lr + 1},{lc + 1}"

    lines = [
        term.bold("GOMOKU"),
        "",
        f"Turn   {turn}",
        f"You    {_stone_swatch(term, G.HUMAN)} black",
        f"AI     {_stone_swatch(term, G.AI)} white",
        f"Last   {last}",
        "",
        term.dim("화살표  이동"),          # arrows  move
        term.dim("enter/space 착수"),                  # enter/space place
        term.dim("r       재시작"),                # r       restart
        term.dim("q       종료"),                      # q       quit
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


def draw(term: Terminal, state: G.GameState) -> None:
    """Compose and print the full frame without clearing the screen."""
    frame: List[str] = [term.home]

    blines = board_lines(term, state)
    for i, line in enumerate(blines):
        frame.append(term.move_xy(BOARD_X, BOARD_Y + i) + _pad(term, line, _ROW_WIDTH))

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

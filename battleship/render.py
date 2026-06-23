"""Render a :class:`game.GameState` to the terminal using blessed.

The whole frame is composed as one string and printed after moving the cursor
home, so there is no full-screen clear between frames and therefore no flicker.
Every line is padded to a fixed printable width (via :func:`_pad`, which counts
visible glyphs with ``term.length`` so colour escapes are ignored) so a shorter
line never leaves stale characters behind from the previous frame.

Two 10x10 grids sit side by side with a fixed gap: the left "MY FLEET" board
shows the human's own ships and where the AI has fired; the right "TRACKING"
board shows the human's shots on the hidden enemy fleet with the aim cursor.
"""
from __future__ import annotations

from typing import List

from blessed import Terminal

import board as B
import game as G

# Layout constants (0-based column positions).
BOARD_X = 2
BOARD_Y = 2
BOARD_GAP = 6          # fixed gap between the two boards
PANEL_GAP = 4
PANEL_WIDTH = 24

# Each cell is two characters wide (glyph + trailing space).
_CELL_W = 2
_LABEL_W = 3           # left row-number gutter ("10 ", " 9 ", ...)
# Printable width of one board block: gutter + COLS cells.
_BOARD_WIDTH = _LABEL_W + B.COLS * _CELL_W
_COLS_LETTERS = "ABCDEFGHIJ"

# Truecolor palette.
_SHIP_RGB = (90, 150, 220)       # own ship block
_SUNK_RGB = (235, 90, 90)        # a sunk ship's cells (both boards)
_HIT_RGB = (235, 90, 90)         # a hit marker
_MISS_RGB = (90, 95, 110)        # a miss marker (dim)
_WATER_RGB = (40, 55, 75)        # untouched water
_CURSOR_RGB = (250, 220, 70)     # aim cursor highlight


def _pad(term: Terminal, text: str, width: int) -> str:
    """Right-pad *text* to a fixed printable width, ignoring colour escapes."""
    extra = width - term.length(text)
    return text + " " * extra if extra > 0 else text


def _glyph(term: Terminal, rgb: tuple, ch: str) -> str:
    """Return a single coloured cell: the glyph plus a trailing space."""
    return term.color_rgb(*rgb)(ch + " ")


def _fleet_cell(term: Terminal, state: G.GameState, pos: B.Pos) -> str:
    """Render one cell of the left MY FLEET board.

    Shows the human's own ships, the AI's hits (red X) and misses (dim dot).
    Cells of a sunk ship are emphasised in the sunk colour.
    """
    shot = pos in state.ai_shots
    ship = G.ship_at(state.player_ships, pos)

    if ship is not None:
        if shot:
            if G.is_sunk(ship, state.ai_shots):
                return _glyph(term, _SUNK_RGB, "#")
            return _glyph(term, _HIT_RGB, "X")
        return _glyph(term, _SHIP_RGB, "O")

    if shot:
        return _glyph(term, _MISS_RGB, ".")
    return _glyph(term, _WATER_RGB, "~")


def _tracking_cell(term: Terminal, state: G.GameState, pos: B.Pos) -> str:
    """Render one cell of the right TRACKING board.

    Shows only the human's shot results on the enemy fleet; ship locations are
    hidden until hit. The aim cursor is highlighted (when play continues).
    """
    is_cursor = pos == state.cursor and not state.game_over
    shot = pos in state.player_shots

    if shot:
        ship = G.ship_at(state.ai_ships, pos)
        if ship is not None:
            rgb = _SUNK_RGB if G.is_sunk(ship, state.player_shots) else _HIT_RGB
            ch = "#" if G.is_sunk(ship, state.player_shots) else "X"
        else:
            rgb, ch = _MISS_RGB, "."
    else:
        rgb, ch = _WATER_RGB, "~"

    if is_cursor:
        return term.reverse(term.color_rgb(*_CURSOR_RGB)(ch + " "))
    return _glyph(term, rgb, ch)


def _board_block(term: Terminal, state: G.GameState, tracking: bool) -> List[str]:
    """Return the lines of one labelled 10x10 board (header + numbered rows)."""
    header = " " * _LABEL_W + "".join(
        term.dim(_COLS_LETTERS[c] + " ") for c in range(B.COLS)
    )
    lines = [header]
    for r in range(B.ROWS):
        gutter = term.dim(f"{r + 1:>2} ")
        cells = [
            _tracking_cell(term, state, (r, c)) if tracking
            else _fleet_cell(term, state, (r, c))
            for c in range(B.COLS)
        ]
        lines.append(gutter + "".join(cells))
    return lines


def board_lines(term: Terminal, state: G.GameState) -> List[str]:
    """Return the two boards laid out side by side, one string per row.

    The left board is MY FLEET and the right board is TRACKING; a title row sits
    above each. Each composed line is the left block, a fixed gap, then the right.
    """
    left = _board_block(term, state, tracking=False)
    right = _board_block(term, state, tracking=True)

    title_left = _pad(term, term.bold("MY FLEET"), _BOARD_WIDTH)
    title_right = term.bold("TRACKING")
    gap = " " * BOARD_GAP

    lines = [title_left + gap + title_right]
    for left_row, right_row in zip(left, right):
        lines.append(_pad(term, left_row, _BOARD_WIDTH) + gap + right_row)
    return lines


def panel_lines(term: Terminal, state: G.GameState) -> List[str]:
    """Return the right-side info panel: title, status, counts, and controls."""
    player_left = G.ships_remaining(state.ai_ships, state.player_shots)
    ai_left = G.ships_remaining(state.player_ships, state.ai_shots)

    if state.game_over:
        turn = "game over"
    elif state.current_turn == G.PLAYER:
        turn = "your fire"
    else:
        turn = "AI firing"

    lines: List[str] = [
        term.bold("BATTLESHIP"),
        "",
        f"Turn       {turn}",
        f"Enemy left {player_left:>2}",
        f"Yours left {ai_left:>2}",
        "",
        term.dim("화살표  조준"),
        term.dim("enter/space 사격"),
        term.dim("r       재시작"),
        term.dim("q       종료"),
    ]

    if state.game_over:
        if state.winner == G.PLAYER:
            banner = term.bold(term.color_rgb(0, 220, 80)("YOU WIN!"))
        else:
            banner = term.bold(term.color_rgb(235, 60, 60)("YOU LOSE"))
        lines.insert(0, banner)
        lines.insert(1, "")

    return lines


def draw(term: Terminal, state: G.GameState) -> None:
    """Compose and print the full frame without clearing the screen."""
    frame: List[str] = [term.home]

    blines = board_lines(term, state)
    board_block_width = _BOARD_WIDTH + BOARD_GAP + _BOARD_WIDTH
    for i, line in enumerate(blines):
        frame.append(
            term.move_xy(BOARD_X, BOARD_Y + i) + _pad(term, line, board_block_width)
        )

    panel_x = BOARD_X + board_block_width + PANEL_GAP
    for i, line in enumerate(panel_lines(term, state)):
        frame.append(
            term.move_xy(panel_x, BOARD_Y + i) + _pad(term, line, PANEL_WIDTH)
        )

    print("".join(frame), end="", flush=True)

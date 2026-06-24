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
PANEL_WIDTH = 24
# The panel grows by two lines when a "pass" notice is shown. panel_lines()
# always pads to this fixed height so the taller frame's trailing control lines
# get overwritten with blanks once the notice disappears (there is no
# full-screen clear between frames). Bump this if the panel gains more lines.
PANEL_HEIGHT = 12

# Each cell is 3 chars wide with no separator: the green background tiles join
# into one continuous board.
_CELL_WIDTH = 3
_ROW_WIDTH = B.SIZE * _CELL_WIDTH

# Truecolor palette.
_BLACK_RGB = (30, 30, 35)        # black disc glyph
_WHITE_RGB = (235, 235, 235)     # white disc glyph
_BOARD_BG = (35, 110, 60)        # green felt
_CURSOR_BG = (90, 170, 110)      # lighter green under the cursor
_MARK_RGB = (210, 230, 180)      # legal-move dot


def _disc_glyph(term: Terminal, player: int) -> str:
    """Return a colored disc glyph for the given player."""
    rgb = _BLACK_RGB if player == G.HUMAN else _WHITE_RGB
    return term.color_rgb(*rgb)("●")  # filled circle


def _cell(
    term: Terminal,
    state: G.GameState,
    row: int,
    col: int,
    legal: set,
) -> str:
    """Render one 3-char cell, including cursor and legal-move decoration."""
    value = state.board[row][col]
    is_cursor = (
        not state.game_over
        and state.current_player == G.HUMAN
        and (row, col) == state.cursor
    )
    bg = _CURSOR_BG if is_cursor else _BOARD_BG

    if value == G.HUMAN:
        inner = " " + _disc_glyph(term, G.HUMAN) + " "
    elif value == G.AI:
        inner = " " + _disc_glyph(term, G.AI) + " "
    elif (row, col) in legal:
        inner = " " + term.color_rgb(*_MARK_RGB)("·") + " "  # middle dot
    else:
        inner = "   "

    return term.on_color_rgb(*bg)(inner)


def _pad(term: Terminal, text: str, width: int) -> str:
    """Right-pad *text* to a fixed printable width, ignoring escape codes."""
    extra = width - term.length(text)
    return text + " " * extra if extra > 0 else text


def board_lines(term: Terminal, state: G.GameState) -> List[str]:
    """Return one string per board row (SIZE rows, top to bottom)."""
    if not state.game_over and state.current_player == G.HUMAN:
        legal = set(G.legal_moves(state.board, G.HUMAN))
    else:
        legal = set()
    lines: List[str] = []
    for r in range(B.SIZE):
        cells = [_cell(term, state, r, c, legal) for c in range(B.SIZE)]
        lines.append("".join(cells))
    return lines


def panel_lines(term: Terminal, state: G.GameState) -> List[str]:
    """Return the right-side info panel, padded to a fixed ``PANEL_HEIGHT``.

    The optional "pass" notice makes the panel vary in length between frames.
    Padding the result to a constant height lets :func:`draw` overwrite the
    trailing rows with blanks, so no stale text lingers when the notice
    disappears (the frame is drawn without a full-screen clear).
    """
    black, white = G.disc_counts(state.board)

    if state.game_over:
        turn = "game over"
    elif state.current_player == G.HUMAN:
        turn = "your move"
    else:
        turn = "AI thinking"

    lines = [
        term.bold("REVERSI"),
        "",
        f"Turn   {turn}",
        f"You    {_disc_glyph(term, G.HUMAN)} black  {black}",
        f"AI     {_disc_glyph(term, G.AI)} white  {white}",
        "",
    ]

    # Pass notice: a pass happened only when the last placement returned the
    # turn to the same player — the opponent had no legal move and was skipped.
    # A bare "waiting side has no move" check yields false positives: the side
    # not to move can be momentarily move-less on an ordinary turn (e.g. right
    # after it just played), without having passed. Gate on the turn actually
    # coming back to whoever made the last move instead.
    last = state.last_move
    turn_returned = (
        last is not None
        and state.board[last[0]][last[1]] == state.current_player
    )
    if not state.game_over and turn_returned:
        passer = G.HUMAN if state.current_player == G.AI else G.AI
        who = "black" if passer == G.HUMAN else "white"
        lines.append(term.dim(f"{who} passes"))
        lines.append("")

    lines.extend([
        term.dim("화살표    이동"),       # arrows: move
        term.dim("enter/space 놓기"),                 # place
        term.dim("r       재시작"),               # restart
        term.dim("q       종료"),                     # quit
    ])

    # Pad to a constant height so a shorter frame overwrites the taller one.
    if len(lines) < PANEL_HEIGHT:
        lines.extend([""] * (PANEL_HEIGHT - len(lines)))
    return lines


def _overlay(term: Terminal, lines: List[str], width: int) -> str:
    """Centre each overlay line over the board's vertical midpoint."""
    y_base = BOARD_Y + B.SIZE // 2 - len(lines) // 2
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

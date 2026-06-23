"""Render a :class:`game.SokobanState` to the terminal using blessed.

The whole frame is composed as one string and printed after moving the cursor
home, so there is no full-screen clear between frames and therefore no flicker.
Every line is padded to a fixed printable width (using ``term.length`` like
tetris/render.py) so a shorter line never leaves stale characters behind.
Padding uses the global MAX_WIDTH / MAX_HEIGHT from levels.py so level
transitions never leave stale rows on screen.
"""
from __future__ import annotations

from typing import List

from blessed import Terminal

import game as G
import levels as L

# Truecolor RGB for each tile type.
_C_WALL       = (80,  80,  80)   # dark grey
_C_FLOOR      = (30,  30,  30)   # very dark (background)
_C_GOAL       = (120, 180, 255)  # bright sky-blue — empty goal target
_C_BOX        = (200, 140,  40)  # amber
_C_BOX_GOAL   = (60,  200,  60)  # green — box sitting on goal
_C_PLAYER     = (240, 240,  60)  # bright yellow
_C_PLR_GOAL   = (60,  240, 240)  # cyan — player on goal

BOARD_X  = 2   # left margin for the grid
BOARD_Y  = 1   # top margin for the grid
PANEL_GAP   = 3
PANEL_WIDTH = 22

# Each cell is rendered as one character wide so a single move steps exactly
# one column horizontally (matching one row vertically).
_CELL_W = 1


def _rgb(term: Terminal, r: int, g: int, b: int, text: str) -> str:
    return term.color_rgb(r, g, b)(text)


def _pad(term: Terminal, text: str, width: int) -> str:
    """Right-pad *text* to a fixed printable *width*, ignoring escape codes."""
    extra = width - term.length(text)
    return text + " " * extra if extra > 0 else text


def _render_cell(
    term: Terminal,
    row: int,
    col: int,
    state: G.SokobanState,
) -> str:
    """Return the single-character escape-coded string for one grid cell."""
    pos = (row, col)
    is_wall  = pos in state.walls
    is_goal  = pos in state.goals
    is_box   = pos in state.boxes
    is_player = pos == state.player

    if is_wall:
        r, g, b = _C_WALL
        return _rgb(term, r, g, b, "#")
    if is_player:
        if is_goal:
            r, g, b = _C_PLR_GOAL
        else:
            r, g, b = _C_PLAYER
        return _rgb(term, r, g, b, "@")
    if is_box:
        if is_goal:
            r, g, b = _C_BOX_GOAL
        else:
            r, g, b = _C_BOX
        return _rgb(term, r, g, b, "$")
    if is_goal:
        r, g, b = _C_GOAL
        return term.bold(_rgb(term, r, g, b, "."))
    # Floor
    r, g, b = _C_FLOOR
    return _rgb(term, r, g, b, " ")


def board_lines(term: Terminal, state: G.SokobanState) -> List[str]:
    """Return one string per row of the level grid.

    All rows are rendered at *L.MAX_HEIGHT* height and *L.MAX_WIDTH* width so
    switching levels never leaves stale characters on screen.
    """
    lines: List[str] = []
    for r in range(L.MAX_HEIGHT):
        row_str = ""
        for c in range(L.MAX_WIDTH):
            if r < state.level_height and c < state.level_width:
                row_str += _render_cell(term, r, c, state)
            else:
                # Pad area outside the current level with plain spaces.
                row_str += " " * _CELL_W
        lines.append(row_str)
    return lines


def panel_lines(term: Terminal, state: G.SokobanState) -> List[str]:
    """Return the sidebar strings: title, stats, and key hints."""
    boxes_remaining = len(state.boxes - state.goals)
    total_goals     = len(state.goals)
    on_goal         = total_goals - boxes_remaining

    lines: List[str] = [
        term.bold("SOKOBAN"),
        "",
        f"Level   {state.level_index + 1:>3} / {len(L.LEVELS)}",
        f"Moves   {state.moves:>5}",
        "",
        f"Boxes on goal",
        f"  {on_goal:>2} / {total_goals:<2}",
        "",
        term.dim("방향키  이동/밀기"),
        term.dim("u       되돌리기"),
        term.dim("r       재시작"),
        term.dim("q       종료"),
    ]
    return lines


def _win_overlay(term: Terminal) -> str:
    """Centre a 'YOU WIN' banner over the board area."""
    text = " YOU WIN!  All levels complete! "
    # Place roughly in the middle of the board area.
    y = BOARD_Y + L.MAX_HEIGHT // 2
    cell_cols = L.MAX_WIDTH * _CELL_W
    x = BOARD_X + max(0, (cell_cols - len(text)) // 2)
    return term.move_xy(x, y) + term.reverse(term.bold(text))


def _solved_overlay(term: Terminal, state: G.SokobanState) -> str:
    """Brief 'Level solved' notice while the player can still press a key."""
    text = f" Level {state.level_index + 1} solved!  Press any key... "
    y = BOARD_Y + L.MAX_HEIGHT // 2
    cell_cols = L.MAX_WIDTH * _CELL_W
    x = BOARD_X + max(0, (cell_cols - len(text)) // 2)
    return term.move_xy(x, y) + term.reverse(term.bold(text))


def draw(term: Terminal, state: G.SokobanState) -> None:
    """Compose and print a full frame without clearing the screen."""
    frame: List[str] = [term.home]

    cell_cols = L.MAX_WIDTH * _CELL_W  # printable width of the grid area

    for i, line in enumerate(board_lines(term, state)):
        frame.append(
            term.move_xy(BOARD_X, BOARD_Y + i) + _pad(term, line, cell_cols)
        )

    panel_x = BOARD_X + cell_cols + PANEL_GAP
    for i, line in enumerate(panel_lines(term, state)):
        frame.append(
            term.move_xy(panel_x, BOARD_Y + i) + _pad(term, line, PANEL_WIDTH)
        )

    if state.won:
        frame.append(_win_overlay(term))
    elif state.solved:
        frame.append(_solved_overlay(term, state))

    print("".join(frame), end="", flush=True)

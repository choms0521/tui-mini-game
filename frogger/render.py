"""Render a GameState to the terminal using blessed.

The full frame is composed as a single string and printed after moving the
cursor home -- no full-screen clear between frames, so there is no flicker.
Every line is padded to a fixed printable width (using term.length) so a
shorter line never leaves stale characters from the previous frame.
"""
from __future__ import annotations

from typing import List

from blessed import Terminal

import board as B
import game as G

# Layout constants.
BOARD_X = 2
BOARD_Y = 1
PANEL_GAP = 3
PANEL_WIDTH = 22

# Printable field width: one char per column + two side borders.
_FIELD_WIDTH = B.WIDTH + 2

# Truecolor palettes.
_ROAD_BG    = (50,  50,  50)   # dark gray road surface
_RIVER_BG   = (20,  60, 120)   # dark blue water
_SAFE_BG    = (30,  90,  30)   # dark green grass
_GOAL_BG    = (10,  50,  10)   # darker green goal bank

_CAR_RGB    = (220,  60,  60)  # red cars
_LOG_RGB    = (150, 100,  40)  # brown logs
_FROG_RGB   = (80,  220,  80)  # bright green frog
_GOAL_EMPTY = (80,  180,  80)  # empty slot highlight
_GOAL_FULL  = (220, 200,  50)  # filled slot highlight

_FROG_GLYPH  = "@"
_CAR_GLYPH   = "C"
_LOG_GLYPH   = "="
_WATER_GLYPH = "~"
_ROAD_GLYPH  = " "
_SAFE_GLYPH  = " "
_SLOT_EMPTY  = "v"
_SLOT_FULL   = "X"


def _pad(term: Terminal, text: str, width: int) -> str:
    """Right-pad *text* to a fixed printable width, ignoring colour escapes."""
    extra = width - term.length(text)
    return text + " " * extra if extra > 0 else text


def _lane_bg(term: Terminal, kind: str, is_goal: bool = False) -> str:
    """Return a terminal colour prefix for a lane's background character."""
    if is_goal:
        r, g, b = _GOAL_BG
    elif kind == "road":
        r, g, b = _ROAD_BG
    elif kind == "river":
        r, g, b = _RIVER_BG
    else:
        r, g, b = _SAFE_BG
    return term.color_rgb(r, g, b)


def field_lines(term: Terminal, state: G.GameState) -> List[str]:
    """Compose the playfield as a list of strings (border + content rows)."""
    border_c   = term.color_rgb(120, 120, 120)
    frog_c     = term.color_rgb(*_FROG_RGB)
    car_c      = term.color_rgb(*_CAR_RGB)
    log_c      = term.color_rgb(*_LOG_RGB)
    water_c    = term.color_rgb(*_RIVER_BG)
    slot_e_c   = term.color_rgb(*_GOAL_EMPTY)
    slot_f_c   = term.color_rgb(*_GOAL_FULL)

    frow, fcol = state.frog

    lines: List[str] = [border_c("+" + "-" * B.WIDTH + "+")]

    for row in range(B.HEIGHT):
        lane = state.lanes[row]
        offset = state.offsets[row]
        obs = B.obstacle_cells(lane, offset)
        cells: List[str] = [border_c("|")]

        for col in range(B.WIDTH):
            is_frog = (row == frow and col == fcol)

            if is_frog:
                cells.append(frog_c(_FROG_GLYPH))
                continue

            if row == B.GOAL_ROW:
                # Check if this column is a goal slot.
                try:
                    slot_idx = B.GOAL_COLS.index(col)
                    if slot_idx in state.filled_goals:
                        cells.append(slot_f_c(_SLOT_FULL))
                    else:
                        cells.append(slot_e_c(_SLOT_EMPTY))
                except ValueError:
                    cells.append(_lane_bg(term, "safe", is_goal=True)(_SAFE_GLYPH))
                continue

            if col in obs:
                if lane.kind == "road":
                    cells.append(car_c(_CAR_GLYPH))
                else:
                    cells.append(log_c(_LOG_GLYPH))
            else:
                if lane.kind == "river":
                    cells.append(water_c(_WATER_GLYPH))
                elif lane.kind == "road":
                    cells.append(_lane_bg(term, "road")(_ROAD_GLYPH))
                else:
                    cells.append(_lane_bg(term, "safe")(_SAFE_GLYPH))

        cells.append(border_c("|"))
        lines.append("".join(cells))

    lines.append(border_c("+" + "-" * B.WIDTH + "+"))
    return lines


def panel_lines(term: Terminal, state: G.GameState) -> List[str]:
    """Compose the right-side information panel as a list of strings."""
    filled = len(state.filled_goals)
    hearts = ("♥ " * state.lives).strip() if state.lives > 0 else ""
    lines = [
        term.bold("FROGGER"),
        "",
        f"Score    {state.score:>6}",
        f"Goals    {filled}/{B.NUM_GOALS}",
        f"Lives    {hearts}",
        "",
        term.dim("화살표  이동"),
        term.dim("p       일시정지"),
        term.dim("r       재시작"),
        term.dim("q       종료"),
    ]
    return lines


def _overlay(term: Terminal, text: str) -> str:
    """Return a centred overlay line positioned in the middle of the field."""
    y = BOARD_Y + B.HEIGHT // 2
    x = BOARD_X + max(0, (_FIELD_WIDTH - len(text) - 2) // 2)
    return term.move_xy(x, y) + term.reverse(term.bold(f" {text} "))


def draw(term: Terminal, state: G.GameState, paused: bool = False) -> None:
    """Print the full frame to the terminal without clearing the screen."""
    frame: List[str] = [term.home]

    for i, line in enumerate(field_lines(term, state)):
        frame.append(
            term.move_xy(BOARD_X, BOARD_Y + i) + _pad(term, line, _FIELD_WIDTH)
        )

    panel_x = BOARD_X + _FIELD_WIDTH + PANEL_GAP
    for i, line in enumerate(panel_lines(term, state)):
        frame.append(
            term.move_xy(panel_x, BOARD_Y + 1 + i) + _pad(term, line, PANEL_WIDTH)
        )

    if state.game_over:
        frame.append(_overlay(term, "GAME OVER  press r"))
    elif state.won:
        frame.append(_overlay(term, "YOU WIN!   press r"))
    elif paused:
        frame.append(_overlay(term, "PAUSED"))

    print("".join(frame), end="", flush=True)

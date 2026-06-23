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
import pieces as P

# Truecolor RGB for each tetromino.
RGB = {
    "I": (0, 240, 240),
    "J": (40, 80, 240),
    "L": (240, 160, 0),
    "O": (240, 220, 0),
    "S": (0, 220, 60),
    "T": (170, 40, 240),
    "Z": (240, 40, 40),
}

BOARD_X = 3
BOARD_Y = 1
PANEL_GAP = 4
PANEL_WIDTH = 20

_CELL_WIDTH = B.WIDTH * 2 + 2  # two columns per cell plus the two side borders


def _fill(term: Terminal, name: str) -> str:
    r, g, b = RGB[name]
    return term.color_rgb(r, g, b)("##")


def _ghost(term: Terminal, name: str) -> str:
    r, g, b = RGB[name]
    return term.color_rgb(r // 3, g // 3, b // 3)("::")


def _empty(term: Terminal) -> str:
    return term.color_rgb(60, 60, 60)(" .")


def _pad(term: Terminal, text: str, width: int) -> str:
    """Right-pad to a fixed printable width, ignoring colour escape codes."""
    extra = width - term.length(text)
    return text + " " * extra if extra > 0 else text


def board_lines(term: Terminal, state: G.GameState) -> List[str]:
    grid = state.grid
    active = set(state.active.cells())
    ghost = set(G.ghost_cells(state)) - active
    name = state.active.name
    border = term.color_rgb(120, 120, 120)

    lines = [border("+" + "--" * B.WIDTH + "+")]
    for r in range(B.HEIGHT):
        cells = [border("|")]
        for c in range(B.WIDTH):
            if (r, c) in active:
                cells.append(_fill(term, name))
            elif grid[r][c] is not None:
                cells.append(_fill(term, grid[r][c]))
            elif (r, c) in ghost:
                cells.append(_ghost(term, name))
            else:
                cells.append(_empty(term))
        cells.append(border("|"))
        lines.append("".join(cells))
    lines.append(border("+" + "--" * B.WIDTH + "+"))
    return lines


def _preview_lines(term: Terminal, state: G.GameState) -> List[str]:
    name = G.next_name(state)
    matrix = P.SHAPES[name]
    rows = ["".join(_fill(term, name) if v else "  " for v in row) for row in matrix]
    while len(rows) < 4:  # keep the preview a stable height
        rows.append("")
    return rows


def panel_lines(term: Terminal, state: G.GameState) -> List[str]:
    lines = [
        term.bold("TETRIS"),
        "",
        "Score",
        term.bold(f"{state.score:>10}"),
        "",
        f"Level   {state.level:>3}",
        f"Lines   {state.lines:>3}",
        "",
        "Next",
    ]
    lines.extend(_preview_lines(term, state))
    lines.extend(
        [
            "",
            term.dim("좌우     이동"),
            term.dim("위/x    회전"),
            term.dim("z       반대 회전"),
            term.dim("아래    천천히 내림"),
            term.dim("space   즉시 내림"),
            term.dim("p       일시정지"),
            term.dim("r       재시작"),
            term.dim("q       종료"),
        ]
    )
    return lines


def _overlay(term: Terminal, text: str) -> str:
    y = BOARD_Y + B.HEIGHT // 2
    x = BOARD_X + max(0, (_CELL_WIDTH - len(text) - 2) // 2)
    return term.move_xy(x, y) + term.reverse(term.bold(f" {text} "))


def draw(term: Terminal, state: G.GameState, paused: bool = False) -> None:
    frame = [term.home]

    for i, line in enumerate(board_lines(term, state)):
        frame.append(term.move_xy(BOARD_X, BOARD_Y + i) + _pad(term, line, _CELL_WIDTH))

    panel_x = BOARD_X + _CELL_WIDTH + PANEL_GAP
    for i, line in enumerate(panel_lines(term, state)):
        frame.append(term.move_xy(panel_x, BOARD_Y + 1 + i) + _pad(term, line, PANEL_WIDTH))

    if state.game_over:
        frame.append(_overlay(term, "GAME OVER  press r"))
    elif paused:
        frame.append(_overlay(term, "PAUSED"))

    print("".join(frame), end="", flush=True)

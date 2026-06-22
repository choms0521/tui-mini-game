"""Render a GameState to the terminal using blessed.

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

# Truecolor RGB for snake and food.
HEAD_RGB  = (80, 220, 80)    # bright green head
BODY_RGB  = (30, 140, 30)    # darker green body
FOOD_RGB  = (240, 60, 60)    # red food
EMPTY_RGB = (40, 40, 40)     # dim empty cell

BOARD_X   = 3
BOARD_Y   = 1
PANEL_GAP = 4
PANEL_WIDTH = 18

# Two columns per cell plus the two side border characters.
_CELL_WIDTH = B.WIDTH * 2 + 2


def _pad(term: Terminal, text: str, width: int) -> str:
    """Right-pad to a fixed printable width, ignoring colour escape codes."""
    extra = width - term.length(text)
    return text + " " * extra if extra > 0 else text


def board_lines(term: Terminal, state: G.GameState) -> List[str]:
    """Compose all rows of the playfield including the border."""
    head = state.body[0] if state.body else None
    body_set = set(state.body[1:])
    border = term.color_rgb(100, 100, 100)

    lines = [border("+" + "--" * B.WIDTH + "+")]
    for r in range(B.HEIGHT):
        cells = [border("|")]
        for c in range(B.WIDTH):
            pos = (r, c)
            if pos == head:
                cells.append(term.color_rgb(*HEAD_RGB)("@@"))
            elif pos in body_set:
                cells.append(term.color_rgb(*BODY_RGB)("##"))
            elif pos == state.food:
                cells.append(term.color_rgb(*FOOD_RGB)("()"))
            else:
                cells.append(term.color_rgb(*EMPTY_RGB)(" ."))
        cells.append(border("|"))
        lines.append("".join(cells))
    lines.append(border("+" + "--" * B.WIDTH + "+"))
    return lines


def panel_lines(term: Terminal, state: G.GameState) -> List[str]:
    """Compose the side panel with title, score, and controls."""
    length = len(state.body)
    lines = [
        term.bold("SNAKE"),
        "",
        "Score",
        term.bold(f"{state.score:>10}"),
        "",
        f"Length  {length:>3}",
        "",
        term.dim("arrows  turn"),
        term.dim("p       pause"),
        term.dim("r       restart"),
        term.dim("q       quit"),
    ]
    return lines


def _overlay(term: Terminal, text: str) -> str:
    y = BOARD_Y + B.HEIGHT // 2
    x = BOARD_X + max(0, (_CELL_WIDTH - len(text) - 2) // 2)
    return term.move_xy(x, y) + term.reverse(term.bold(f" {text} "))


def draw(term: Terminal, state: G.GameState, paused: bool = False) -> None:
    """Compose and print a full frame to the terminal without flickering."""
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

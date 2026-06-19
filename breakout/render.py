"""Render a Breakout :class:`game.GameState` to the terminal with blessed.

The whole frame is composed and printed after moving the cursor home, with each
line padded to a fixed width, so there is no full-screen clear and no flicker.
"""
from __future__ import annotations

from typing import List

from blessed import Terminal

import config as C
import game as G

BOARD_X = 2
BOARD_Y = 1
PANEL_GAP = 3
PANEL_WIDTH = 18

_BORDER_RGB = (120, 120, 120)
_BALL = "O"
_PADDLE = "="
_BRICK = "#"


def _pad(term: Terminal, text: str, width: int) -> str:
    extra = width - term.length(text)
    return text + " " * extra if extra > 0 else text


def _cell(term: Terminal, state: G.GameState, x: int, y: int) -> str:
    ball = state.ball
    if x == ball.x and y == ball.y:
        return term.bold_white(_BALL)
    if y == C.PADDLE_ROW and state.paddle_x <= x < state.paddle_x + C.PADDLE_W:
        return term.bold(term.color_rgb(220, 220, 220)(_PADDLE))
    brick = G.brick_at(state.bricks, x, y)
    if brick is not None:
        return term.color_rgb(*C.BRICK_RGB[brick[0]])(_BRICK)
    return " "


def board_lines(term: Terminal, state: G.GameState) -> List[str]:
    border = term.color_rgb(*_BORDER_RGB)
    edge = border("+" + "-" * C.PLAY_W + "+")
    lines = [edge]
    for y in range(C.PLAY_H):
        cells = [border("|")]
        for x in range(C.PLAY_W):
            cells.append(_cell(term, state, x, y))
        cells.append(border("|"))
        lines.append("".join(cells))
    lines.append(edge)
    return lines


def panel_lines(term: Terminal, state: G.GameState) -> List[str]:
    return [
        term.bold("BREAKOUT"),
        "",
        "Score",
        term.bold(f"{state.score:>10}"),
        "",
        f"Lives   {state.lives:>3}",
        f"Level   {state.level:>3}",
        "",
        term.dim("left/right move"),
        term.dim("space   launch"),
        term.dim("p       pause"),
        term.dim("r       restart"),
        term.dim("q       quit"),
    ]


def _overlay(term: Terminal, text: str) -> str:
    y = BOARD_Y + 1 + C.PLAY_H // 2
    x = BOARD_X + 1 + max(0, (C.PLAY_W - len(text) - 2) // 2)
    return term.move_xy(x, y) + term.reverse(term.bold(f" {text} "))


def draw(term: Terminal, state: G.GameState, paused: bool = False) -> None:
    frame = [term.home]

    for i, line in enumerate(board_lines(term, state)):
        frame.append(term.move_xy(BOARD_X, BOARD_Y + i) + _pad(term, line, C.PLAY_W + 2))

    panel_x = BOARD_X + C.PLAY_W + 2 + PANEL_GAP
    for i, line in enumerate(panel_lines(term, state)):
        frame.append(term.move_xy(panel_x, BOARD_Y + 1 + i) + _pad(term, line, PANEL_WIDTH))

    if state.game_over:
        frame.append(_overlay(term, "GAME OVER  press r"))
    elif paused:
        frame.append(_overlay(term, "PAUSED"))
    elif not state.launched:
        frame.append(_overlay(term, "press SPACE to launch"))

    print("".join(frame), end="", flush=True)

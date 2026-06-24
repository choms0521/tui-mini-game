"""Render a Pong :class:`game.GameState` to the terminal with blessed.

The whole frame is composed and printed after moving the cursor home, with each
line padded to a fixed printable width so there is no full-screen clear and no
flicker between frames.
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
_PADDLE = "|"
_CENTER_LINE = ":"

# Detailed how-to shown as a centered overlay when the player presses ``h``.
# Korean for players; keep each line width within the court width.
HELP_LINES = [
    "PONG  —  AI와 패들 대결",
    "",
    "위/아래 방향키 또는 w/s   패들 이동",
    "space                    서브/일시정지",
    "r 재시작   q 종료",
    "",
    "위/아래 방향키(또는 w/s)로 패들을 움직여",
    "공을 막고 받아칩니다. 상대가 못 받으면",
    "점수를 얻고, 먼저 목표 점수에 도달하면 승리.",
    "",
    "h 키로 도움말을 닫습니다",
]


def _pad(term: Terminal, text: str, width: int) -> str:
    """Pad *text* to *width* printable columns (ignores escape sequences)."""
    extra = width - term.length(text)
    return text + " " * extra if extra > 0 else text


def _cell(term: Terminal, state: G.GameState, x: int, y: int) -> str:
    """Return the styled character for a single court cell."""
    # Ball
    if x == state.ball_x and y == state.ball_y:
        return term.bold_white(_BALL)

    # Left paddle
    if x == C.LEFT_PADDLE_X and state.left_y <= y < state.left_y + C.PADDLE_H:
        return term.bold(term.color_rgb(80, 200, 255)(_PADDLE))

    # Right paddle
    if x == C.RIGHT_PADDLE_X and state.right_y <= y < state.right_y + C.PADDLE_H:
        return term.bold(term.color_rgb(255, 160, 80)(_PADDLE))

    # Dashed center line
    if x == C.PLAY_W // 2 and y % 2 == 0:
        return term.dim(_CENTER_LINE)

    return " "


def board_lines(term: Terminal, state: G.GameState) -> List[str]:
    """Build the list of styled strings for the court (border + interior)."""
    border = term.color_rgb(*_BORDER_RGB)
    top_bottom = border("+" + "-" * C.PLAY_W + "+")

    # Score header inside the top border row area.
    score_str = f"{state.left_score}  {state.right_score}"
    score_x = (C.PLAY_W - len(score_str)) // 2
    score_line = (
        border("|")
        + " " * score_x
        + term.bold(score_str)
        + " " * (C.PLAY_W - score_x - len(score_str))
        + border("|")
    )

    lines = [top_bottom, score_line]
    for y in range(C.PLAY_H):
        cells = [border("|")]
        for x in range(C.PLAY_W):
            cells.append(_cell(term, state, x, y))
        cells.append(border("|"))
        lines.append("".join(cells))
    lines.append(top_bottom)
    return lines


def panel_lines(term: Terminal, state: G.GameState) -> List[str]:
    """Build the side panel with title and controls."""
    return [
        term.bold("PONG"),
        "",
        term.dim("AI와 패들 대결."),
        term.dim("공을 받아쳐"),
        term.dim("상대 골문에"),
        term.dim("먼저 넣으세요."),
        "",
        term.color_rgb(80, 200, 255)("Player") + "  vs  " + term.color_rgb(255, 160, 80)("CPU"),
        "",
        term.dim("위/w    패들 위로"),
        term.dim("아래/s  패들 아래"),
        term.dim("space   시작/정지"),
        term.dim("h       도움말"),
        term.dim("r       재시작"),
        term.dim("q       종료"),
    ]


def _overlay(term: Terminal, text: str) -> str:
    """Return an escape string that prints a centred overlay message."""
    # +2 for the two border columns, +1 for the score line
    y = BOARD_Y + 1 + 1 + C.PLAY_H // 2
    x = BOARD_X + 1 + max(0, (C.PLAY_W - len(text) - 2) // 2)
    return term.move_xy(x, y) + term.reverse(term.bold(f" {text} "))


def help_overlay(term: Terminal, lines: List[str]) -> str:
    """Render *lines* as a centered reverse-video block over the court."""
    inner = max(term.length(l) for l in lines)
    # +1 for the top border, +1 for the score line.
    x = BOARD_X + 1 + max(0, (C.PLAY_W - inner - 2) // 2)
    y = BOARD_Y + 1 + 1 + max(0, (C.PLAY_H - len(lines)) // 2)
    parts: List[str] = []
    for i, line in enumerate(lines):
        pad = inner - term.length(line)
        parts.append(term.move_xy(x, y + i) + term.reverse(term.bold(" " + line + " " * pad + " ")))
    return "".join(parts)


def draw(term: Terminal, state: G.GameState, show_help: bool = False) -> None:
    """Compose and flush a complete frame without clearing the screen."""
    frame = [term.home]

    lines = board_lines(term, state)
    for i, line in enumerate(lines):
        frame.append(
            term.move_xy(BOARD_X, BOARD_Y + i)
            + _pad(term, line, C.PLAY_W + 2)
        )

    panel_x = BOARD_X + C.PLAY_W + 2 + PANEL_GAP
    for i, line in enumerate(panel_lines(term, state)):
        frame.append(
            term.move_xy(panel_x, BOARD_Y + 1 + i)
            + _pad(term, line, PANEL_WIDTH)
        )

    if show_help:
        frame.append(help_overlay(term, HELP_LINES))
    elif state.game_over:
        frame.append(_overlay(term, f"{state.winner} wins!  press r"))
    elif state.paused:
        frame.append(_overlay(term, "PAUSED"))
    elif not state.started:
        frame.append(_overlay(term, "press SPACE to serve"))

    print("".join(frame), end="", flush=True)

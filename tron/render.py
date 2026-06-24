"""Render a GameState to the terminal using blessed.

The whole frame is composed as one string and printed after moving the cursor
home, so there is no full-screen clear between frames and therefore no flicker.
Every line is padded to a fixed printable width so a shorter line never leaves
stale characters behind from the previous frame.
"""
from __future__ import annotations

from typing import List

from blessed import Terminal

import board as B
import game as G

# Truecolor RGB for each cycle's head and trail, plus the empty cell.
PLAYER_HEAD_RGB  = (90, 220, 255)    # bright cyan head
PLAYER_TRAIL_RGB = (40, 130, 170)    # dim cyan trail
AI_HEAD_RGB      = (255, 120, 90)    # bright orange head
AI_TRAIL_RGB     = (170, 70, 45)     # dim orange trail
EMPTY_RGB        = (30, 30, 36)      # dim empty cell
BORDER_RGB       = (110, 110, 120)

BOARD_X = 3
BOARD_Y = 1
PANEL_GAP = 4
PANEL_WIDTH = 22

# Two columns per cell plus the two side border characters.
_CELL_WIDTH = B.WIDTH * 2 + 2


def _pad(term: Terminal, text: str, width: int) -> str:
    """Right-pad to a fixed printable width, ignoring color escape codes."""
    extra = width - term.length(text)
    return text + " " * extra if extra > 0 else text


def board_lines(term: Terminal, state: G.GameState) -> List[str]:
    """Compose all rows of the playfield including the border."""
    player_trail = state.player_trail
    ai_trail = state.ai_trail
    player_head = state.player_pos if state.player_alive else None
    ai_head = state.ai_pos if state.ai_alive else None
    border = term.color_rgb(*BORDER_RGB)

    lines = [border("+" + "--" * B.WIDTH + "+")]
    for r in range(B.HEIGHT):
        cells = [border("|")]
        for c in range(B.WIDTH):
            pos = (r, c)
            if pos == player_head:
                cells.append(term.color_rgb(*PLAYER_HEAD_RGB)("@@"))
            elif pos == ai_head:
                cells.append(term.color_rgb(*AI_HEAD_RGB)("@@"))
            elif pos in player_trail:
                cells.append(term.color_rgb(*PLAYER_TRAIL_RGB)("##"))
            elif pos in ai_trail:
                cells.append(term.color_rgb(*AI_TRAIL_RGB)("##"))
            else:
                cells.append(term.color_rgb(*EMPTY_RGB)(" ."))
        cells.append(border("|"))
        lines.append("".join(cells))
    lines.append(border("+" + "--" * B.WIDTH + "+"))
    return lines


def panel_lines(term: Terminal, state: G.GameState) -> List[str]:
    """Compose the side panel with title, status, legend, and controls."""
    if state.game_over:
        status = "game over"
    elif not state.player_alive:
        status = "crashed"
    else:
        status = "racing"
    player_mark = term.color_rgb(*PLAYER_HEAD_RGB)("@")
    ai_mark = term.color_rgb(*AI_HEAD_RGB)("@")
    lines = [
        term.bold("TRON"),
        "",
        f"Tick   {state.tick:>5}",
        f"Status {status}",
        "",
        f"You    {player_mark} cyan",
        f"AI     {ai_mark} orange",
        "",
        term.dim("화살표  방향"),
        term.dim("p       일시정지"),
        term.dim("r       재시작"),
        term.dim("q       종료"),
    ]
    return lines


def _overlay(term: Terminal, lines: List[str], width: int) -> str:
    """Center each overlay line over the board's vertical midpoint."""
    y_base = BOARD_Y + 1 + B.HEIGHT // 2 - len(lines) // 2
    parts: List[str] = []
    for i, text in enumerate(lines):
        visible = term.length(text)
        x = BOARD_X + max(0, (width - visible) // 2)
        parts.append(term.move_xy(x, y_base + i) + text)
    return "".join(parts)


def draw(term: Terminal, state: G.GameState, paused: bool = False) -> None:
    """Compose and print a full frame to the terminal without flickering."""
    frame: List[str] = [term.home]

    for i, line in enumerate(board_lines(term, state)):
        frame.append(term.move_xy(BOARD_X, BOARD_Y + i) + _pad(term, line, _CELL_WIDTH))

    panel_x = BOARD_X + _CELL_WIDTH + PANEL_GAP
    for i, line in enumerate(panel_lines(term, state)):
        frame.append(term.move_xy(panel_x, BOARD_Y + 1 + i) + _pad(term, line, PANEL_WIDTH))

    if state.game_over:
        if state.winner == G.PLAYER:
            banner = term.bold(term.color_rgb(*PLAYER_HEAD_RGB)(" YOU WIN! "))
        elif state.winner == G.AI:
            banner = term.bold(term.color_rgb(*AI_HEAD_RGB)(" AI WINS "))
        else:
            banner = term.bold(term.yellow(" DRAW "))
        frame.append(_overlay(term, [banner, term.dim(" r to retry ")], _CELL_WIDTH))
    elif paused:
        frame.append(_overlay(term, [term.bold(term.reverse(" PAUSED "))], _CELL_WIDTH))

    print("".join(frame), end="", flush=True)

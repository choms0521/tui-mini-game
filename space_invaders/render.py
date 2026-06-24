"""Render a GameState to the terminal using blessed.

The whole frame is composed as one string and printed after moving the cursor
home, so there is no full-screen clear between frames and therefore no flicker.
Every line is padded to a fixed printable width (using term.length like
tetris/render.py) so a shorter line never leaves stale characters behind.
"""
from __future__ import annotations

from typing import List

from blessed import Terminal

import board as B
import game as G

# Display constants.
BOARD_X = 2          # left margin for the playfield
BOARD_Y = 1          # top margin for the playfield
PANEL_GAP = 3        # gap between field right edge and the side panel
PANEL_WIDTH = 20     # fixed width for the side panel

# Printable width of the playfield: one char per column + two side borders.
_FIELD_WIDTH = B.WIDTH + 2

# Truecolor RGB for alien rows (cycles through FLEET_ROWS from top).
_ALIEN_COLORS = [
    (240, 80, 80),    # row 0: red
    (240, 180, 40),   # row 1: orange
    (80, 220, 80),    # row 2: green
    (80, 160, 240),   # row 3: blue
]

# Glyphs.
_PLAYER_GLYPH = "^"
_BULLET_GLYPH = "|"
_ALIEN_GLYPH = "W"
_EMPTY_GLYPH = " "

# Detailed how-to shown as a centered overlay when the player presses ``h``.
# Korean for players; keep each line width within the playfield width.
HELP_LINES = [
    "SPACE INVADERS  —  인베이더",
    "",
    "좌우 방향키        함선 이동",
    "space             총알 발사",
    "p 일시정지  r 재시작  q 종료",
    "",
    "좌우로 함선을 움직이고 space로",
    "총알을 발사합니다. 외계인은 좌우로",
    "움직이다 끝에 닿으면 한 칸 내려옵니다.",
    "모두 맞히면 승리, 함대가 바닥에",
    "닿으면 패배.",
    "",
    "h 키로 도움말을 닫습니다",
]


def _pad(term: Terminal, text: str, width: int) -> str:
    """Right-pad *text* to a fixed printable width, ignoring colour escapes."""
    extra = width - term.length(text)
    return text + " " * extra if extra > 0 else text


def _alien_color(term: Terminal, row: int) -> str:
    """Return a colored alien glyph based on the alien's row index."""
    idx = row % len(_ALIEN_COLORS)
    r, g, b = _ALIEN_COLORS[idx]
    return term.color_rgb(r, g, b)(_ALIEN_GLYPH)


def field_lines(term: Terminal, state: G.GameState) -> List[str]:
    """Compose the playfield as a list of strings (border + content rows)."""
    border = term.color_rgb(120, 120, 120)
    bullet_color = term.color_rgb(255, 255, 100)
    player_color = term.color_rgb(100, 200, 255)

    alien_set = {(r, c): r for r, c in state.aliens}
    bullet_set = set(state.bullets)

    lines = [border("+" + "-" * B.WIDTH + "+")]

    for row in range(B.HEIGHT):
        cells: List[str] = [border("|")]
        for col in range(B.WIDTH):
            pos = (row, col)
            if row == B.PLAYER_ROW and col == state.player_col:
                cells.append(player_color(_PLAYER_GLYPH))
            elif pos in bullet_set:
                cells.append(bullet_color(_BULLET_GLYPH))
            elif pos in alien_set:
                alien_row = alien_set[pos]
                cells.append(_alien_color(term, alien_row))
            else:
                cells.append(_EMPTY_GLYPH)
        cells.append(border("|"))
        lines.append("".join(cells))

    lines.append(border("+" + "-" * B.WIDTH + "+"))
    return lines


def panel_lines(term: Terminal, state: G.GameState) -> List[str]:
    """Compose the right-side information panel as a list of strings."""
    remaining = len(state.aliens)
    lines = [
        term.bold("INVADERS"),
        "",
        term.dim("내려오는 외계인"),
        term.dim("함대를 모두"),
        term.dim("격추하세요."),
        term.dim("바닥에 닿으면 패배."),
        "",
        "Score",
        term.bold(f"{state.score:>10}"),
        "",
        f"Aliens  {remaining:>3}",
        "",
        term.dim("좌우     이동"),
        term.dim("space   발사"),
        term.dim("p       일시정지"),
        term.dim("h       도움말"),
        term.dim("r       재시작"),
        term.dim("q       종료"),
    ]
    return lines


def _overlay(term: Terminal, text: str) -> str:
    """Return a centred overlay line positioned in the middle of the field."""
    y = BOARD_Y + B.HEIGHT // 2
    x = BOARD_X + max(0, (_FIELD_WIDTH - len(text) - 2) // 2)
    return term.move_xy(x, y) + term.reverse(term.bold(f" {text} "))


def help_overlay(term: Terminal, lines: List[str]) -> str:
    """Render *lines* as a centered reverse-video block over the playfield."""
    inner = max(term.length(l) for l in lines)
    x = BOARD_X + max(0, (_FIELD_WIDTH - inner - 2) // 2)
    y = BOARD_Y + max(0, (B.HEIGHT - len(lines)) // 2)
    parts: List[str] = []
    for i, line in enumerate(lines):
        pad = inner - term.length(line)
        parts.append(term.move_xy(x, y + i) + term.reverse(term.bold(" " + line + " " * pad + " ")))
    return "".join(parts)


def draw(term: Terminal, state: G.GameState, paused: bool = False, show_help: bool = False) -> None:
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

    if show_help:
        frame.append(help_overlay(term, HELP_LINES))
    elif state.game_over:
        frame.append(_overlay(term, "GAME OVER  press r"))
    elif state.won:
        frame.append(_overlay(term, "YOU WIN!   press r"))
    elif paused:
        frame.append(_overlay(term, "PAUSED"))

    print("".join(frame), end="", flush=True)

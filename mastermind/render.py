"""Render a :class:`game.GameState` to the terminal using blessed.

The whole frame is composed as one string and printed after moving the cursor
home, so there is no full-screen clear between frames and therefore no flicker.
Every line is padded to a fixed width so a shorter line never leaves stale
characters behind from the previous frame.
"""
from __future__ import annotations

from typing import List

from blessed import Terminal

import game as G

# Layout constants
BOARD_X = 3
BOARD_Y = 1
PANEL_GAP = 4
PANEL_WIDTH = 22

# Each peg is rendered as a 3-char cell ``[#]`` with one space between cells.
_PEG_WIDTH = 3
_PEG_SEP = 1
_PEGS_WIDTH = G.CODE_LENGTH * (_PEG_WIDTH + _PEG_SEP) - _PEG_SEP

# A guess row is the peg block, a gap, then the feedback markers.
_FEEDBACK_GAP = 2
# _feedback_markers renders CODE_LENGTH single-cell markers joined by spaces,
# so its printable width is CODE_LENGTH markers + (CODE_LENGTH - 1) separators.
_FEEDBACK_WIDTH = 2 * G.CODE_LENGTH - 1
_ROW_WIDTH = _PEGS_WIDTH + _FEEDBACK_GAP + _FEEDBACK_WIDTH

# Distinct truecolor per color value (index 0 unused; colors are 1..6).
_COLOR_RGB = {
    1: (220, 60, 60),    # red
    2: (60, 140, 240),   # blue
    3: (70, 200, 90),    # green
    4: (235, 200, 60),   # yellow
    5: (200, 90, 220),   # magenta
    6: (90, 210, 215),   # cyan
}
_EMPTY_RGB = (40, 40, 40)        # dim slot in the active/blank row
_EXACT_RGB = (235, 235, 235)     # filled marker for an exact peg
_PARTIAL_RGB = (150, 150, 150)   # hollow marker for a partial peg
_MISS_RGB = (55, 55, 55)         # unlit feedback marker


def _peg(term: Terminal, color: int) -> str:
    """Render a single colored peg cell, or a dim empty slot for color 0."""
    if color in _COLOR_RGB:
        r, g, b = _COLOR_RGB[color]
        return term.color_rgb(r, g, b)(f"[{color}]")
    r, g, b = _EMPTY_RGB
    return term.color_rgb(r, g, b)(" . ")


def _peg_cells(term: Terminal, code: G.Code) -> List[str]:
    """Render exactly ``CODE_LENGTH`` peg cells, padding short rows with blanks."""
    cells = [_peg(term, code[i] if i < len(code) else 0) for i in range(G.CODE_LENGTH)]
    return cells


def _feedback_markers(term: Terminal, feedback: G.Feedback) -> str:
    """Render the feedback for a guess as filled/hollow/unlit markers.

    Filled circle = an exact peg, hollow circle = a partial peg, dot = neither.
    The markers do not reveal which guess position they refer to, matching the
    classic Mastermind rule.
    """
    exact, partial = feedback
    markers: List[str] = []
    for _ in range(exact):
        markers.append(term.color_rgb(*_EXACT_RGB)("●"))   # filled circle
    for _ in range(partial):
        markers.append(term.color_rgb(*_PARTIAL_RGB)("○"))  # hollow circle
    for _ in range(G.CODE_LENGTH - exact - partial):
        markers.append(term.color_rgb(*_MISS_RGB)("·"))     # middle dot
    return " ".join(markers)


def _pad(term: Terminal, text: str, width: int) -> str:
    """Right-pad *text* to a fixed printable width, ignoring escape codes."""
    extra = width - term.length(text)
    return text + " " * extra if extra > 0 else text


def board_lines(term: Terminal, state: G.GameState) -> List[str]:
    """Return one string per board row (``max_guesses`` rows total).

    Submitted guesses show their pegs and feedback markers; the next row shows
    the in-progress input (no feedback yet); remaining rows are blank slots.
    """
    lines: List[str] = []
    for row_idx in range(state.max_guesses):
        if row_idx < len(state.guesses):
            cells = _peg_cells(term, state.guesses[row_idx])
            feedback = _feedback_markers(term, state.feedbacks[row_idx])
        elif row_idx == len(state.guesses) and not state.game_over:
            cells = _peg_cells(term, state.current)
            feedback = ""
        else:
            cells = _peg_cells(term, ())
            feedback = ""
        pegs = (" " * _PEG_SEP).join(cells)
        lines.append(pegs + " " * _FEEDBACK_GAP + feedback)
    return lines


def panel_lines(term: Terminal, state: G.GameState) -> List[str]:
    """Return the right-side info panel as a list of strings."""
    guesses_left = state.max_guesses - len(state.guesses)
    lines = [
        term.bold("MASTERMIND"),
        "",
        term.dim("숨겨진 색 코드를"),
        term.dim("제한된 시도 안에"),
        term.dim("추론해 맞히세요."),
        "",
        f"Guesses left  {guesses_left:>2}",
        "",
        term.dim("1-6    색 선택"),
        term.dim("←/bksp 지우기"),
        term.dim("enter  제출"),
        term.dim("h      도움말"),
        term.dim("r      재시작"),
        term.dim("q      종료"),
        "",
        term.dim("● exact  ○ partial"),
    ]
    return lines


def help_overlay(term: Terminal, lines: List[str]) -> str:
    """Render *lines* as a centered reverse-video block over the playfield."""
    inner = max(term.length(l) for l in lines)
    x = BOARD_X + 1 + max(0, (_ROW_WIDTH - inner - 2) // 2)
    y = BOARD_Y + 1
    parts: List[str] = []
    for i, line in enumerate(lines):
        pad = inner - term.length(line)
        parts.append(
            term.move_xy(x, y + i) + term.reverse(term.bold(" " + line + " " * pad + " "))
        )
    return "".join(parts)


# Detailed how-to shown as a centered overlay when the player presses ``h``.
# Korean for players.
HELP_LINES = [
    "MASTERMIND",
    "",
    "숫자 키로 4칸의 색을 고르고",
    "enter로 제출합니다.",
    "검은 페그=색·위치 모두 맞음,",
    "흰 페그=색은 있으나 위치 틀림.",
    "이 단서로 코드를 좁혀",
    "제한 횟수 안에 맞히면 승리.",
    "",
    "1-6    색 선택",
    "enter  제출  r  재시작",
    "h 키로 도움말을 닫습니다",
]


def _overlay(term: Terminal, lines: List[str], board_pixel_width: int) -> str:
    """Centre each overlay line horizontally over the board, in its upper-middle band."""
    y_base = BOARD_Y + len(lines)  # keep the banner near the top-middle band
    parts: List[str] = []
    for i, text in enumerate(lines):
        visible = term.length(text)
        x = BOARD_X + max(0, (board_pixel_width - visible) // 2)
        parts.append(term.move_xy(x, y_base + i) + text)
    return "".join(parts)


def _secret_reveal(term: Terminal, secret: G.Code) -> str:
    """Render the secret code as colored pegs for the end-of-game reveal."""
    return (" " * _PEG_SEP).join(_peg(term, color) for color in secret)


def draw(term: Terminal, state: G.GameState, show_help: bool = False) -> None:
    """Compose and print the full frame without clearing the screen."""
    frame: List[str] = [term.home]

    blines = board_lines(term, state)
    for i, line in enumerate(blines):
        frame.append(term.move_xy(BOARD_X, BOARD_Y + i) + _pad(term, line, _ROW_WIDTH))

    panel_x = BOARD_X + _ROW_WIDTH + PANEL_GAP
    plines = panel_lines(term, state)
    for i, line in enumerate(plines):
        frame.append(term.move_xy(panel_x, BOARD_Y + i) + _pad(term, line, PANEL_WIDTH))

    if show_help:
        frame.append(help_overlay(term, HELP_LINES))
    elif state.game_over:
        # Win/lose banner with the secret revealed, centred over the board.
        if state.won:
            banner = term.bold(term.green(" YOU CRACKED IT! "))
        else:
            banner = term.bold(term.red(" OUT OF GUESSES "))
        overlay_lines = [
            banner,
            term.reverse(" SECRET ") + " " + _secret_reveal(term, state.secret),
            term.dim(" r to retry "),
        ]
        frame.append(_overlay(term, overlay_lines, _ROW_WIDTH))

    print("".join(frame), end="", flush=True)

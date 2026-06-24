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
PANEL_WIDTH = 24

# Each tile: 3 chars wide + 1 space separator; 5 tiles per row.
_TILE_WIDTH = 3
_TILE_SEP = 1
_ROW_WIDTH = G.WORD_LENGTH * (_TILE_WIDTH + _TILE_SEP) - _TILE_SEP  # 19

# Detailed how-to shown as a centered overlay when the player presses ``?``
# (Wordle uses ``?`` only, since ``h`` is a valid guess letter). Korean for players.
# The board is only 19 cols wide, so the modal is wider/taller than the board;
# help_overlay centers it against the terminal so it stays on screen.
HELP_LINES = [
    "WORDLE  —  단어 맞히기",
    "",
    "a-z    글자 입력",
    "enter  추측 제출",
    "bksp   지우기",
    "r 재시작   q 종료",
    "",
    "a~z로 다섯 글자를 입력하고",
    "enter로 제출합니다. 글자는",
    "초록(자리·글자 모두 맞음),",
    "노랑(글자는 있으나 자리 틀림),",
    "회색(없음)으로 표시됩니다.",
    "backspace로 지우고 여섯 번",
    "안에 맞히면 승리. 끝나면 r.",
    "",
    "? 키로 도움말을 닫습니다",
]

# Truecolor RGB for tile states.
_GREEN = (83, 141, 78)
_YELLOW = (181, 159, 59)
_GRAY = (58, 58, 60)
_EMPTY = (18, 18, 19)
_BORDER_EMPTY = (58, 58, 60)
_BORDER_FILLED = (86, 87, 88)


def _tile(term: Terminal, letter: str, score: G.Score | None, active: bool) -> str:
    """Render a single 3-char tile with colour background."""
    ch = f" {letter} " if letter else "   "
    if score is G.Score.GREEN:
        r, g, b = _GREEN
    elif score is G.Score.YELLOW:
        r, g, b = _YELLOW
    elif score is G.Score.GRAY:
        r, g, b = _GRAY
    elif active and letter:
        # typed but not yet submitted: slightly brighter empty
        r, g, b = _BORDER_FILLED
    else:
        r, g, b = _EMPTY
    return term.on_color_rgb(r, g, b)(term.bold(ch) if letter else ch)


def _pad(term: Terminal, text: str, width: int) -> str:
    """Right-pad *text* to a fixed printable width, ignoring escape codes."""
    extra = width - term.length(text)
    return text + " " * extra if extra > 0 else text


def board_lines(term: Terminal, state: G.GameState) -> List[str]:
    """Return one string per grid row (6 rows total)."""
    lines: List[str] = []
    for row_idx in range(G.MAX_TRIES):
        if row_idx < len(state.guesses):
            word = state.guesses[row_idx]
            score_row = state.scores[row_idx]
            tiles = [_tile(term, word[c], score_row[c], False) for c in range(G.WORD_LENGTH)]
        elif row_idx == len(state.guesses) and not state.game_over:
            # Active row: show what the player has typed so far.
            word = state.current.ljust(G.WORD_LENGTH)
            tiles = [_tile(term, word[c] if word[c] != " " else "", None, True) for c in range(G.WORD_LENGTH)]
        else:
            tiles = [_tile(term, "", None, False) for _ in range(G.WORD_LENGTH)]
        lines.append((" " * _TILE_SEP).join(tiles))
    return lines


def panel_lines(term: Terminal, state: G.GameState) -> List[str]:
    """Return the right-side info panel as a list of strings."""
    tries_left = G.MAX_TRIES - len(state.guesses)
    lines = [
        term.bold("WORDLE"),
        "",
        term.dim("숨겨진 5글자 단어를"),
        term.dim("여섯 번 안에 맞히세요."),
        term.dim("초록=정위치, 노랑=있음."),
        "",
        f"Tries left  {tries_left:>2}",
        "",
        term.dim("a-z     글자 입력"),
        term.dim("bksp    지우기"),
        term.dim("enter   추측 제출"),
        term.dim("?       도움말"),
        term.dim("r       재시작(종료 후)"),
        term.dim("q       종료"),
    ]
    return lines


def help_overlay(term: Terminal, lines: List[str]) -> str:
    """Render *lines* as a centered reverse-video block over the board."""
    board_height = G.MAX_TRIES * 2  # each tile row is two terminal rows tall
    inner = max(term.length(l) for l in lines)
    x = BOARD_X + max(0, (_ROW_WIDTH - inner - 2) // 2)
    # The overlay is taller than the board, so center it against the full terminal
    # height when known (falling back to the board area when run headless).
    screen_height = term.height or (BOARD_Y + board_height)
    y = max(0, (screen_height - len(lines)) // 2)
    parts: List[str] = []
    for i, line in enumerate(lines):
        pad = inner - term.length(line)
        parts.append(term.move_xy(x, y + i) + term.reverse(term.bold(" " + line + " " * pad + " ")))
    return "".join(parts)


def _overlay(term: Terminal, lines: List[str], board_pixel_width: int) -> str:
    """Centre each overlay line over the board at the vertical midpoint."""
    y_base = BOARD_Y + G.MAX_TRIES // 2
    parts: List[str] = []
    for i, text in enumerate(lines):
        visible = term.length(text)
        x = BOARD_X + max(0, (board_pixel_width - visible) // 2)
        parts.append(term.move_xy(x, y_base + i) + text)
    return "".join(parts)


def draw(term: Terminal, state: G.GameState, show_help: bool = False) -> None:
    """Compose and print the full frame without clearing the screen."""
    frame: List[str] = [term.home]

    blines = board_lines(term, state)
    # Each board row is two terminal rows tall (tile + blank separator).
    for i, line in enumerate(blines):
        frame.append(term.move_xy(BOARD_X, BOARD_Y + i * 2) + _pad(term, line, _ROW_WIDTH))
        frame.append(term.move_xy(BOARD_X, BOARD_Y + i * 2 + 1) + _pad(term, "", _ROW_WIDTH))

    panel_x = BOARD_X + _ROW_WIDTH + PANEL_GAP
    plines = panel_lines(term, state)
    for i, line in enumerate(plines):
        frame.append(term.move_xy(panel_x, BOARD_Y + i) + _pad(term, line, PANEL_WIDTH))

    # Notice line below the board.
    notice_y = BOARD_Y + G.MAX_TRIES * 2 + 1
    if state.notice:
        notice_text = term.bold(term.yellow(state.notice))
    else:
        notice_text = ""
    frame.append(term.move_xy(BOARD_X, notice_y) + _pad(term, notice_text, _ROW_WIDTH + PANEL_GAP + PANEL_WIDTH))

    # Help overlay takes precedence; otherwise the win/lose overlay shows.
    if show_help:
        frame.append(help_overlay(term, HELP_LINES))
    elif state.game_over:
        if state.won:
            overlay_lines = [
                term.bold(term.green(" YOU WIN! ")),
                term.reverse(f" {state.answer} "),
                term.dim(" r to retry "),
            ]
        else:
            overlay_lines = [
                term.bold(term.red(" GAME OVER ")),
                term.reverse(f" {state.answer} "),
                term.dim(" r to retry "),
            ]
        frame.append(_overlay(term, overlay_lines, _ROW_WIDTH))

    print("".join(frame), end="", flush=True)

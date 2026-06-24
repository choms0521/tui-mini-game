"""Render a :class:`game.GameState` to the terminal using blessed.

The whole frame is composed as one string and printed after ``term.home``
so there is no full-screen clear between frames and therefore no flicker.
Every line is padded to a fixed printable width so a shorter line never
leaves stale characters from the previous frame.
"""
from __future__ import annotations

from typing import List

from blessed import Terminal

import dungeon as D
import game as G

# Panel layout
MAP_X = 2
MAP_Y = 1
PANEL_GAP = 3
PANEL_WIDTH = 20

# Detailed how-to shown as a centered overlay when the player presses ``h``/``?``.
# Korean for players; each line stays within the dungeon map width.
HELP_LINES = [
    "ROGUELIKE  —  로그라이크",
    "",
    "방향키  이동/공격",
    "r 재시작   q 종료",
    "",
    "방향키로 이동하고 몬스터가 있는",
    "칸으로 들어가면 공격합니다.",
    "물약(!)은 체력 회복, 장비(/)는",
    "능력 강화. 계단(>)에 닿으면 다음",
    "층으로 내려갑니다. 체력이 0이",
    "되면 게임 오버. r 재시작.",
    "",
    "h 키로 도움말을 닫습니다",
]

# Truecolor RGB for dungeon tiles and entities.
_CLR_WALL = (60, 60, 80)
_CLR_FLOOR = (100, 100, 100)
_CLR_STAIRS = (220, 180, 50)
_CLR_PLAYER = (50, 220, 255)
_CLR_RAT = (180, 130, 80)
_CLR_GOBLIN = (100, 200, 80)
_CLR_POTION = (200, 80, 200)
_CLR_GEAR = (220, 180, 50)

_MONSTER_COLORS = {
    "r": _CLR_RAT,
    "g": _CLR_GOBLIN,
}


def _pad(term: Terminal, text: str, width: int) -> str:
    """Right-pad ``text`` to ``width`` printable characters."""
    extra = width - term.length(text)
    return text + " " * extra if extra > 0 else text


def _tile_str(term: Terminal, state: G.GameState, col: int, row: int) -> str:
    """Return the coloured string for a single map tile."""
    p = state.player

    # Player
    if col == p.col and row == p.row:
        r, g, b = _CLR_PLAYER
        return term.color_rgb(r, g, b)("@")

    # Monsters
    for m in state.monsters:
        if m.col == col and m.row == row:
            r, g, b = _MONSTER_COLORS.get(m.glyph, _CLR_GOBLIN)
            return term.color_rgb(r, g, b)(m.glyph)

    # Items
    for item in state.items:
        if item.col == col and item.row == row:
            if item.kind == G.POTION:
                r, g, b = _CLR_POTION
                return term.color_rgb(r, g, b)("!")
            else:
                r, g, b = _CLR_GEAR
                return term.color_rgb(r, g, b)("/")

    tile = state.grid[row][col]
    if tile == D.WALL:
        r, g, b = _CLR_WALL
        return term.color_rgb(r, g, b)("#")
    if tile == D.STAIRS:
        r, g, b = _CLR_STAIRS
        return term.color_rgb(r, g, b)(">")
    # Floor
    r, g, b = _CLR_FLOOR
    return term.color_rgb(r, g, b)(".")


def map_lines(term: Terminal, state: G.GameState) -> List[str]:
    """Return one coloured string per row of the dungeon map."""
    grid = state.grid
    lines = []
    for row in range(len(grid)):
        cells = [_tile_str(term, state, col, row) for col in range(len(grid[row]))]
        lines.append("".join(cells))
    return lines


def _hp_bar(term: Terminal, hp: int, max_hp: int, width: int = 12) -> str:
    """Return a coloured HP bar of fixed printable ``width``."""
    filled = max(0, round(hp / max_hp * width)) if max_hp > 0 else 0
    bar = term.color_rgb(50, 200, 50)("#" * filled) + term.color_rgb(80, 80, 80)(
        "-" * (width - filled)
    )
    return "[" + bar + "]"


def panel_lines(term: Terminal, state: G.GameState) -> List[str]:
    """Return lines for the right-side information panel."""
    p = state.player
    lines = [
        term.bold("ROGUELIKE"),
        "",
        term.dim("던전을 탐험하며"),
        term.dim("몬스터를 처치하고"),
        term.dim("깊이 내려가세요."),
        "",
        "HP",
        _hp_bar(term, p.hp, p.max_hp),
        f"{p.hp:>3} / {p.max_hp}",
        "",
        f"ATK  {p.attack:>3}",
        f"LVL  {state.depth:>3}",
        f"SCR  {state.score:>5}",
        "",
        term.dim("방향키  이동/공격"),
        term.dim("> 에 닿으면 하강"),
        term.dim("h       도움말"),
        term.dim("r       재시작"),
        term.dim("q       종료"),
        "",
        "몬스터:",
        term.color_rgb(*_CLR_RAT)("r") + " 쥐",
        term.color_rgb(*_CLR_GOBLIN)("g") + " 고블린",
        "",
        "아이템:",
        term.color_rgb(*_CLR_POTION)("!") + " 물약",
        term.color_rgb(*_CLR_GEAR)("/") + " 장비",
    ]
    return lines


def help_overlay(term: Terminal, state: G.GameState, lines: List[str]) -> str:
    """Render *lines* as a centered reverse-video block over the dungeon map."""
    map_w = len(state.grid[0]) if state.grid else D.WIDTH
    map_h = len(state.grid) if state.grid else D.HEIGHT
    inner = max(term.length(l) for l in lines)
    x = MAP_X + max(0, (map_w - inner - 2) // 2)
    y = MAP_Y + max(0, (map_h - len(lines)) // 2)
    parts: List[str] = []
    for i, line in enumerate(lines):
        pad = inner - term.length(line)
        parts.append(term.move_xy(x, y + i) + term.reverse(term.bold(" " + line + " " * pad + " ")))
    return "".join(parts)


def _overlay(term: Terminal, state: G.GameState, text: str) -> str:
    """Centre an overlay message on the map area."""
    map_w = len(state.grid[0]) if state.grid else D.WIDTH
    map_h = len(state.grid) if state.grid else D.HEIGHT
    y = MAP_Y + map_h // 2
    x = MAP_X + max(0, (map_w - len(text) - 2) // 2)
    return term.move_xy(x, y) + term.reverse(term.bold(f" {text} "))


def draw(term: Terminal, state: G.GameState, show_help: bool = False) -> None:
    """Compose and print a complete flicker-free frame."""
    map_w = len(state.grid[0]) if state.grid else D.WIDTH
    frame: List[str] = [term.home]

    for i, line in enumerate(map_lines(term, state)):
        frame.append(
            term.move_xy(MAP_X, MAP_Y + i) + _pad(term, line, map_w)
        )

    panel_x = MAP_X + map_w + PANEL_GAP
    for i, line in enumerate(panel_lines(term, state)):
        frame.append(
            term.move_xy(panel_x, MAP_Y + i) + _pad(term, line, PANEL_WIDTH)
        )

    if show_help:
        frame.append(help_overlay(term, state, HELP_LINES))
    elif state.game_over:
        frame.append(
            _overlay(term, state, f"DEAD  depth:{state.depth}  score:{state.score}  r=restart q=quit")
        )

    print("".join(frame), end="", flush=True)

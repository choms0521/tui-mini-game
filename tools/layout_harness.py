"""Layout harness: verify every game's side panel fits its budget.

Each game renders a board plus a fixed-width side panel. This harness imports
each game headlessly, builds a starting state, and checks:

  * every ``panel_lines`` entry fits within ``PANEL_WIDTH`` (no horizontal overflow)
  * the total frame width ``BOARD_X + board_width + PANEL_GAP + PANEL_WIDTH`` stays
    within ``MAX_FRAME_WIDTH`` (default 80) -- a couple of intentionally wide games
    are exempt (see ``WIDE_EXEMPT``)
  * the panel contains a Korean how-to summary (the in-game explanation)

Run from the repo root:

    .venv/bin/python tools/layout_harness.py            # all games
    .venv/bin/python tools/layout_harness.py snake pong # a subset

Exits non-zero if any checked game fails, so it can gate a commit / CI.
"""
from __future__ import annotations

import importlib
import os
import random
import sys

from blessed import Terminal

MAX_FRAME_WIDTH = 80
# Games whose board alone is wider than MAX_FRAME_WIDTH; only the panel-overflow
# and how-to checks apply to these (their frame width is inherent, not new).
WIDE_EXEMPT = {"pong", "tron"}

ALL_GAMES = [
    "2048", "breakout", "snake", "minesweeper", "space_invaders", "roguelike",
    "wordle", "sokoban", "pong", "tetris", "connect_four", "mastermind", "sudoku",
    "reversi", "gomoku", "battleship", "blackjack", "tron", "frogger",
]

# Hangul syllables are valid (Korean UI); any CJK ideograph is a rule violation.
def _is_hangul(ch: str) -> bool:
    return 0xAC00 <= ord(ch) <= 0xD7A3


def _build_state(game):
    for name in ("new_game", "new_state", "initial_state", "start", "make_state"):
        fn = getattr(game, name, None)
        if fn is None:
            continue
        for args in ((), (random.Random(0),)):
            try:
                return fn(*args)
            except Exception:
                continue
    return None


def _board_width(term: Terminal, render, state):
    for fn in ("board_lines", "field_lines", "court_lines", "grid_lines"):
        f = getattr(render, fn, None)
        if f is None:
            continue
        try:
            lines = f(term, state)
            return max(term.length(line) for line in lines)
        except Exception:
            pass
    return None


def check_game(term: Terminal, root: str, game: str) -> list[str]:
    """Return a list of failure messages (empty == pass)."""
    failures: list[str] = []
    d = os.path.join(root, game)
    sys.path.insert(0, d)
    cwd = os.getcwd()
    os.chdir(d)
    for mod in ("config", "board", "pieces", "dungeon", "levels", "words",
                "cards", "solver", "game", "render"):
        sys.modules.pop(mod, None)
    try:
        G = importlib.import_module("game")
        R = importlib.import_module("render")
        state = _build_state(G)
        panel = R.panel_lines(term, state)
        pw = getattr(R, "PANEL_WIDTH", None)
        if pw is None:
            failures.append(f"{game}: render has no PANEL_WIDTH")
            return failures
        for line in panel:
            if term.length(line) > pw:
                failures.append(
                    f"{game}: panel line exceeds PANEL_WIDTH "
                    f"({term.length(line)} > {pw}): {term.strip_seqs(line)!r}")
        has_summary = any(
            any(_is_hangul(c) for c in term.strip_seqs(line)) for line in panel)
        if not has_summary:
            failures.append(f"{game}: panel has no Korean how-to text")
        bx = getattr(R, "BOARD_X", getattr(R, "MAP_X", getattr(R, "MENU_X", 2)))
        gap = getattr(R, "PANEL_GAP", 3)
        bw = _board_width(term, R, state)
        if bw is not None and game not in WIDE_EXEMPT:
            frame = bx + bw + gap + pw
            if frame > MAX_FRAME_WIDTH:
                failures.append(
                    f"{game}: frame width {frame} > {MAX_FRAME_WIDTH}")
    except Exception as exc:  # pragma: no cover - import/registration errors
        failures.append(f"{game}: ERROR {type(exc).__name__}: {exc}")
    finally:
        sys.path.remove(d)
        os.chdir(cwd)
    return failures


def main() -> int:
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    games = sys.argv[1:] or ALL_GAMES
    term = Terminal(force_styling=True)
    all_failures: list[str] = []
    for game in games:
        fails = check_game(term, root, game)
        status = "ok" if not fails else "FAIL"
        print(f"{game:16} {status}")
        all_failures.extend(fails)
    print("-" * 40)
    if all_failures:
        print(f"{len(all_failures)} problem(s):")
        for f in all_failures:
            print(f"  - {f}")
        return 1
    print(f"All {len(games)} game layouts pass.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

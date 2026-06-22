"""Entry point for the mini-game launcher.

A blessed menu that runs each game as a *separate process* and returns to the
menu when the game exits. Running games as children means their identically
named modules (``game`` / ``render``) never collide, and the launcher never has
to import game code at all.

The blessed context is always exited before a child runs and re-entered
afterwards, so the launcher and the game never fight over terminal state
(cbreak / fullscreen / hidden cursor). Get that boundary wrong and the terminal
is left garbled after the first game; keeping ``subprocess.run`` outside every
``with term...()`` block is what keeps it clean.

Run with ``python launcher/main.py`` (or the bundled ``play.sh``).
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from typing import Sequence, Tuple

from blessed import Terminal

import discover as D
import render as R

# The launcher lives in ``<root>/launcher``; games are folders under ``<root>``.
ROOT = Path(__file__).resolve().parent.parent


def _menu(term: Terminal, games: Sequence, selected: int) -> Tuple[str, int]:
    """Draw the menu and read keys until the user picks a game or quits.

    Returns ``("play", index)`` or ``("quit", index)``. Runs entirely inside the
    blessed context; the caller leaves the context before launching a game.
    """
    with term.fullscreen(), term.cbreak(), term.hidden_cursor():
        print(term.home + term.clear, end="", flush=True)
        while True:
            R.draw(term, games, selected)
            key = term.inkey()
            if key.name == "KEY_UP":
                selected = (selected - 1) % len(games)
            elif key.name == "KEY_DOWN":
                selected = (selected + 1) % len(games)
            elif key.name == "KEY_ENTER" or str(key) in ("\n", "\r"):
                return "play", selected
            elif str(key).lower() == "q":
                return "quit", selected


def _report_crash(term: Terminal, game: D.Game, code: int) -> None:
    """Pause on a nonzero exit so the child's traceback stays readable."""
    print(
        term.normal
        + f"\n'{game.name}' exited abnormally (code {code}). "
        + "Press any key to return to the menu...",
        end="",
        flush=True,
    )
    with term.cbreak():
        term.inkey()


def run() -> None:
    term = Terminal()
    games = D.discover_games(ROOT)
    if not games:
        print("No games found next to the launcher.")
        return

    selected = 0
    while True:
        action, selected = _menu(term, games, selected)
        if action == "quit":
            break

        game = games[selected]
        # Launch OUTSIDE the blessed context: blessed has restored the terminal
        # on context exit, so the child owns a clean terminal of its own.
        result = subprocess.run([sys.executable, str(game.entry)])
        if result.returncode != 0:
            _report_crash(term, game, result.returncode)

    print(term.normal + "Thanks for playing!\n", end="")


if __name__ == "__main__":
    run()

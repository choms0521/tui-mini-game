"""Entry point: terminal setup, keyboard input, and the main game loop.

Run with ``python main.py``.  Pressing ``q`` makes ``run()`` return cleanly
so the launcher can redraw its menu.
"""
from __future__ import annotations

import random

from blessed import Terminal

import game as G
import render as R

POLL_TIMEOUT = 0.05   # seconds; kept short so the terminal stays responsive


def _map_key(key) -> str | None:
    """Translate a blessed keystroke into a game action name."""
    if key.name == "KEY_LEFT":
        return "left"
    if key.name == "KEY_RIGHT":
        return "right"
    if key.name == "KEY_UP":
        return "up"
    if key.name == "KEY_DOWN":
        return "down"
    char = str(key).lower()
    return {"q": "quit", "r": "restart"}.get(char)


def run() -> None:
    """Set up the terminal, run the game loop, and return when the player quits."""
    term = Terminal()
    rng = random.Random()
    state = G.new_game(rng)
    dirty = True

    with term.fullscreen(), term.cbreak(), term.hidden_cursor():
        print(term.home + term.clear, end="", flush=True)
        try:
            while True:
                if dirty:
                    R.draw(term, state)
                    dirty = False

                key = term.inkey(timeout=POLL_TIMEOUT)
                if not key:
                    continue

                action = _map_key(key)
                if action == "quit":
                    break
                if action == "restart":
                    state = G.new_game(rng)
                    dirty = True
                elif action in ("left", "right", "up", "down"):
                    new_state = G.move(state, action, rng)
                    if new_state is not state:
                        state = new_state
                        dirty = True
        except KeyboardInterrupt:
            pass

    print(term.normal + "Thanks for playing 2048!\n", end="")


if __name__ == "__main__":
    run()

"""Entry point: terminal setup, keyboard input, and the main game loop.

Run with ``python main.py`` (or via the launcher). Sudoku is turn-based: the
loop blocks on a keystroke and only redraws when the state actually changes,
so it consumes no CPU while the player thinks.
"""
from __future__ import annotations

import random

from blessed import Terminal

import game as G
import render as R

# Cursor movement deltas for the arrow keys.
_MOVES = {
    "up": (-1, 0),
    "down": (1, 0),
    "left": (0, -1),
    "right": (0, 1),
}


def _map_key(key) -> str | None:
    """Translate a blessed keystroke into a game action name."""
    if key.name == "KEY_UP":
        return "up"
    if key.name == "KEY_DOWN":
        return "down"
    if key.name == "KEY_LEFT":
        return "left"
    if key.name == "KEY_RIGHT":
        return "right"
    # Backspace can arrive as KEY_BACKSPACE, KEY_DELETE, or the raw DEL byte
    # ("\x7f") depending on the terminal, so accept all three for the clear action.
    if key.name in ("KEY_BACKSPACE", "KEY_DELETE") or str(key) == "\x7f":
        return "clear"

    char = str(key)
    if char in "123456789":
        return char  # set that digit
    if char in ("0", " "):
        return "clear"
    lowered = char.lower()
    return {
        "q": "quit",
        "r": "restart",
    }.get(lowered)


def _apply(state: G.GameState, action: str, rng: random.Random) -> G.GameState:
    """Apply a non-quit action and return the resulting state."""
    if action in _MOVES:
        dr, dc = _MOVES[action]
        return G.move_cursor(state, dr, dc)
    if action == "clear":
        return G.clear_value(state)
    if action == "restart":
        return G.restart(rng, state)
    if action in "123456789":
        return G.set_value(state, int(action))
    return state


def run() -> None:
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

                key = term.inkey()
                if not key:
                    continue
                action = _map_key(key)
                if action == "quit":
                    break
                if action is None:
                    continue
                new_state = _apply(state, action, rng)
                if new_state is not state:
                    state = new_state
                    dirty = True
        except KeyboardInterrupt:
            pass

    print(term.normal + "Thanks for playing Sudoku!\n", end="")


if __name__ == "__main__":
    run()

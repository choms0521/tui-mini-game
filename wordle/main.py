"""Entry point: terminal setup, keyboard input, and the main game loop.

Run with ``python main.py`` (or via the launcher).  The loop blocks on
``term.inkey`` waiting for player input; there is no tick/gravity so no
timeout is needed.
"""
from __future__ import annotations

import random

from blessed import Terminal

import game as G
import render as R


def _map_key(key) -> str | None:
    """Translate a blessed keystroke into an action name."""
    # Backspace comes in as KEY_BACKSPACE, KEY_DELETE, or the raw DEL byte.
    if key.name in ("KEY_BACKSPACE", "KEY_DELETE") or str(key) == "\x7f":
        return "backspace"
    if key.name == "KEY_ENTER" or str(key) == "\r" or str(key) == "\n":
        return "enter"

    char = str(key).lower()
    if char == "q":
        return "quit"
    # ``h`` is a needed letter (153 of the words contain H), so only ``?``
    # toggles the help overlay here.
    if char == "?":
        return "help"
    if char.isalpha() and len(char) == 1:
        return f"letter:{char}"
    return None


def run() -> None:
    """Run Wordle; returns when the player presses q."""
    term = Terminal()
    rng = random.Random()
    state = G.new_game(rng)
    show_help = False
    dirty = True

    with term.fullscreen(), term.cbreak(), term.hidden_cursor():
        print(term.home + term.clear, end="", flush=True)
        try:
            while True:
                if dirty:
                    R.draw(term, state, show_help=show_help)
                    dirty = False

                key = term.inkey()
                if not key:
                    continue

                action = _map_key(key)

                if action == "quit":
                    break

                if action == "help":
                    show_help = not show_help
                    dirty = True
                    continue

                # While the help overlay is open, swallow every other key.
                if show_help:
                    continue

                if state.game_over:
                    # Only quit and restart (r) are meaningful after game ends.
                    if action == "letter:r":
                        state = G.new_game(rng)
                        dirty = True
                    continue

                if action == "backspace":
                    new_state = G.delete_letter(state)
                    if new_state is not state:
                        state = new_state
                        dirty = True
                elif action == "enter":
                    new_state = G.submit_guess(state)
                    if new_state is not state:
                        state = new_state
                        dirty = True
                elif action and action.startswith("letter:"):
                    letter = action[len("letter:"):]
                    new_state = G.type_letter(state, letter)
                    if new_state is not state:
                        state = new_state
                        dirty = True

        except KeyboardInterrupt:
            pass

    print(term.normal + "Thanks for playing Wordle!\n", end="")


if __name__ == "__main__":
    run()

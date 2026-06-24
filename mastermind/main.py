"""Entry point: terminal setup, keyboard input, and the main game loop.

Run with ``python main.py`` (or via the launcher). The loop blocks on
``term.inkey`` waiting for player input; there is no tick/gravity so no timeout
is needed.
"""
from __future__ import annotations

import random

from blessed import Terminal

import game as G
import render as R


def _map_key(key) -> str | None:
    """Translate a blessed keystroke into an action name."""
    # Backspace and Left both undo the last placed peg.
    if key.name in ("KEY_BACKSPACE", "KEY_DELETE", "KEY_LEFT") or str(key) == "\x7f":
        return "backspace"
    if key.name == "KEY_ENTER" or str(key) in ("\r", "\n"):
        return "enter"

    char = str(key).lower()
    if char == "q":
        return "quit"
    if char == "r":
        return "restart"
    if char in ("h", "?"):
        return "help"
    if char.isdigit() and 1 <= int(char) <= G.NUM_COLORS:
        return f"color:{char}"
    return None


def run() -> None:
    """Run Mastermind; returns when the player presses q."""
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

                if action == "restart":
                    show_help = False
                    state = G.new_game(rng)
                    dirty = True
                    continue

                if show_help or state.game_over:
                    # Only quit, help, and restart are meaningful while help is shown
                    # or after the game ends.
                    continue

                if action == "backspace":
                    new_state = G.delete_peg(state)
                elif action == "enter":
                    new_state = G.submit_guess(state)
                elif action and action.startswith("color:"):
                    color = int(action[len("color:"):])
                    new_state = G.set_peg(state, color)
                else:
                    new_state = state

                if new_state is not state:
                    state = new_state
                    dirty = True

        except KeyboardInterrupt:
            pass

    print(term.normal + "Thanks for playing Mastermind!\n", end="")


if __name__ == "__main__":
    run()

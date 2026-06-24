"""Entry point: terminal setup, keyboard input, and the main game loop.

Run with ``python main.py`` (or via the launcher). Blackjack is turn-based: the
loop blocks on ``term.inkey`` waiting for a keystroke and only redraws when the
state changes. There is no tick, so no timeout is needed.
"""
from __future__ import annotations

import random

from blessed import Terminal

import game as G
import render as R


def _map_key(key) -> str | None:
    """Translate a blessed keystroke into a game action name."""
    char = str(key).lower()
    # ``h`` is HIT in blackjack, so only ``?`` toggles the help overlay.
    return {
        "h": "hit",
        "s": "stand",
        "r": "restart",
        "q": "quit",
        "?": "help",
    }.get(char)


def run() -> None:
    """Run Blackjack; returns when the player presses q."""
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
                    state = G.new_game(rng)
                    show_help = False
                    dirty = True
                    continue
                if show_help or state.game_over:
                    # While help is open (or once the hand ends) ignore play keys.
                    continue

                if action == "hit":
                    new_state = G.hit(state)
                elif action == "stand":
                    new_state = G.stand(state)
                else:
                    new_state = state

                if new_state is not state:
                    state = new_state
                    dirty = True
        except KeyboardInterrupt:
            pass

    print(term.normal + "Thanks for playing Blackjack!\n", end="")


if __name__ == "__main__":
    run()

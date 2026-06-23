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
    return {
        "h": "hit",
        "s": "stand",
        "r": "restart",
        "q": "quit",
    }.get(char)


def run() -> None:
    """Run Blackjack; returns when the player presses q."""
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
                if action == "restart":
                    state = G.new_game(rng)
                    dirty = True
                    continue
                if state.game_over:
                    # Only restart (r) and quit (q) matter once the hand ends.
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

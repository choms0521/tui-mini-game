"""Entry point: terminal setup, keyboard input, and the main game loop.

Run with ``python main.py`` (or via the launcher). Connect Four is turn-based:
the loop blocks on a keystroke and only redraws when the state changes. After
the human drops a disc the AI replies immediately within the same iteration.
"""
from __future__ import annotations

import random

from blessed import Terminal

import board as B
import game as G
import render as R


def _map_key(key) -> str | None:
    """Translate a blessed keystroke into a game action name."""
    if key.name == "KEY_LEFT":
        return "left"
    if key.name == "KEY_RIGHT":
        return "right"
    if key.name in ("KEY_ENTER", "KEY_DOWN") or str(key) in ("\r", "\n", " "):
        return "drop"
    char = str(key).lower()
    return {"q": "quit", "r": "restart"}.get(char)


def run() -> None:
    term = Terminal()
    rng = random.Random()
    state = G.new_game()
    selected = B.COLS // 2
    dirty = True

    with term.fullscreen(), term.cbreak(), term.hidden_cursor():
        print(term.home + term.clear, end="", flush=True)
        try:
            while True:
                if dirty:
                    R.draw(term, state, selected)
                    dirty = False

                key = term.inkey()
                if not key:
                    continue
                action = _map_key(key)

                if action == "quit":
                    break
                if action == "restart":
                    state = G.new_game()
                    selected = B.COLS // 2
                    dirty = True
                    continue
                if state.game_over:
                    continue

                if action == "left" and selected > 0:
                    selected -= 1
                    dirty = True
                elif action == "right" and selected < B.COLS - 1:
                    selected += 1
                    dirty = True
                elif action == "drop":
                    moved = G.drop(state, selected)
                    if moved is not state:
                        state = moved
                        # Let the AI reply if the game is still going.
                        if not state.game_over and state.current_player == G.AI:
                            R.draw(term, state, selected)  # show the "AI thinking" panel
                            col = G.ai_move(state, rng)
                            if col is not None:
                                state = G.drop(state, col)
                        dirty = True
        except KeyboardInterrupt:
            pass

    print(term.normal + "Thanks for playing Connect Four!\n", end="")


if __name__ == "__main__":
    run()

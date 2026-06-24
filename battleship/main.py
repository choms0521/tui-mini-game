"""Entry point: terminal setup, keyboard input, and the main game loop.

Run with ``python main.py`` (or via the launcher). Battleship is turn-based: the
loop blocks on a keystroke and only redraws when the state changes. The arrows
move the aim cursor on the tracking board; firing resolves the human's shot and,
if the game is still going, the AI replies within the same iteration.
"""
from __future__ import annotations

import random

from blessed import Terminal

import game as G
import render as R


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
    if key.name == "KEY_ENTER" or str(key) in ("\r", "\n", " "):
        return "fire"
    char = str(key).lower()
    return {"q": "quit", "r": "restart"}.get(char)


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
                if action == "restart":
                    state = G.new_game(rng)
                    dirty = True
                    continue
                if state.game_over:
                    continue

                if action == "up":
                    moved = G.move_cursor(state, -1, 0)
                elif action == "down":
                    moved = G.move_cursor(state, 1, 0)
                elif action == "left":
                    moved = G.move_cursor(state, 0, -1)
                elif action == "right":
                    moved = G.move_cursor(state, 0, 1)
                elif action == "fire":
                    fired = G.player_fire(state)
                    if fired is not state:
                        state = fired
                        # Let the AI reply if the game is still going.
                        if not state.game_over and state.current_turn == G.AI:
                            R.draw(term, state)  # show the "AI firing" panel
                            state = G.ai_fire(state, rng)
                        dirty = True
                    continue
                else:
                    continue

                if moved is not state:
                    state = moved
                    dirty = True
        except KeyboardInterrupt:
            pass

    print(term.normal + "Thanks for playing Battleship!\n", end="")


if __name__ == "__main__":
    run()

"""Entry point: terminal setup, keyboard input, and the main game loop.

Run with ``python main.py`` (or via the launcher). Gomoku is turn-based: the
loop blocks on a keystroke and only redraws when the state changes. After the
human places a stone the AI replies immediately within the same iteration.
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
        return "place"
    char = str(key).lower()
    return {"q": "quit", "r": "restart", "h": "help", "?": "help"}.get(char)


_MOVES = {
    "up": (-1, 0),
    "down": (1, 0),
    "left": (0, -1),
    "right": (0, 1),
}


def run() -> None:
    """Run Gomoku; returns when the player presses q."""
    term = Terminal()
    rng = random.Random()
    state = G.new_game()
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
                    state = G.new_game()
                    show_help = False
                    dirty = True
                    continue
                if show_help or state.game_over:
                    continue

                if action in _MOVES:
                    drow, dcol = _MOVES[action]
                    moved = G.move_cursor(state, drow, dcol)
                    if moved is not state:
                        state = moved
                        dirty = True
                elif action == "place":
                    moved = G.place(state)
                    if moved is not state:
                        state = moved
                        # Let the AI reply if the game is still going.
                        if not state.game_over and state.current_player == G.AI:
                            R.draw(term, state)  # show the "AI thinking" panel
                            aim = state.cursor   # keep the human's aim after the reply
                            pos = G.ai_move(state, rng)
                            if pos is not None:
                                state = G.place_at(state, pos)
                                state = G.set_cursor(state, aim)
                        dirty = True
        except KeyboardInterrupt:
            pass

    print(term.normal + "Thanks for playing Gomoku!\n", end="")


if __name__ == "__main__":
    run()

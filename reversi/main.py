"""Entry point: terminal setup, keyboard input, and the main game loop.

Run with ``python main.py`` (or via the launcher). Reversi is turn-based: the
loop blocks on a keystroke and only redraws when the state changes. After the
human places a disc the AI replies immediately, and because turns do not strictly
alternate the AI keeps moving while it is still its turn (the human auto-passed).
"""
from __future__ import annotations

import random
from dataclasses import replace

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
    if key.name == "KEY_UP":
        return "up"
    if key.name == "KEY_DOWN":
        return "down"
    if key.name == "KEY_ENTER" or str(key) in ("\r", "\n", " "):
        return "place"
    char = str(key).lower()
    return {"q": "quit", "r": "restart"}.get(char)


def _move_cursor(state: G.GameState, drow: int, dcol: int) -> G.GameState:
    """Return a state with the cursor nudged and clamped inside the board."""
    row, col = state.cursor
    row = max(0, min(B.SIZE - 1, row + drow))
    col = max(0, min(B.SIZE - 1, col + dcol))
    return replace(state, cursor=(row, col))


def _run_ai(state: G.GameState, term: Terminal, rng: random.Random) -> G.GameState:
    """Let the AI play out its consecutive turns, redrawing as it thinks."""
    while not state.game_over and state.current_player == G.AI:
        R.draw(term, state)  # show the "AI thinking" panel before searching
        pos = G.ai_move(state, rng)
        if pos is None:
            break
        state = G.place(state, pos)
    return state


def run() -> None:
    term = Terminal()
    rng = random.Random()
    state = G.new_game()
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
                    state = G.new_game()
                    dirty = True
                    continue
                if state.game_over:
                    continue

                if action == "left":
                    state = _move_cursor(state, 0, -1)
                    dirty = True
                elif action == "right":
                    state = _move_cursor(state, 0, 1)
                    dirty = True
                elif action == "up":
                    state = _move_cursor(state, -1, 0)
                    dirty = True
                elif action == "down":
                    state = _move_cursor(state, 1, 0)
                    dirty = True
                elif action == "place":
                    moved = G.place(state, state.cursor)
                    if moved is not state:
                        state = _run_ai(moved, term, rng)
                        dirty = True
        except KeyboardInterrupt:
            pass

    print(term.normal + "Thanks for playing Reversi!\n", end="")


if __name__ == "__main__":
    run()

"""Entry point: terminal setup, keyboard input, and the Frogger game loop.

Run with ``python main.py``. The loop polls for a key with a short timeout so
obstacles keep scrolling in real time even when no key is pressed.
Input order each iteration: read key -> apply movement -> advance tick -> redraw.
"""
from __future__ import annotations

import time

from blessed import Terminal

import game as G
import render as R

# Seconds per game tick (obstacle scroll rate).
TICK_INTERVAL = 0.15

# How long inkey() waits before returning an empty keystroke.
POLL_TIMEOUT = 0.02


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
    char = str(key).lower()
    return {
        "q": "quit",
        "p": "pause",
        "h": "help",
        "?": "help",
        "r": "restart",
    }.get(char)


def run() -> None:
    term = Terminal()
    state = G.new_game()
    paused = False
    show_help = False
    dirty = True
    last_tick = time.monotonic()

    with term.fullscreen(), term.cbreak(), term.hidden_cursor():
        print(term.home + term.clear, end="", flush=True)
        try:
            while True:
                if dirty:
                    R.draw(term, state, paused=paused, show_help=show_help)
                    dirty = False

                key = term.inkey(timeout=POLL_TIMEOUT)
                if key:
                    action = _map_key(key)
                    if action == "quit":
                        break
                    elif action == "help":
                        show_help = not show_help
                        last_tick = time.monotonic()
                        dirty = True
                    elif action == "pause":
                        paused = not paused
                        last_tick = time.monotonic()
                        dirty = True
                    elif action == "restart":
                        state = G.new_game()
                        paused = False
                        show_help = False
                        last_tick = time.monotonic()
                        dirty = True
                    elif action and not paused and not show_help and not state.game_over and not state.won:
                        if action == "up":
                            new_state = G.move_frog(state, -1, 0)
                        elif action == "down":
                            new_state = G.move_frog(state, +1, 0)
                        elif action == "left":
                            new_state = G.move_frog(state, 0, -1)
                        elif action == "right":
                            new_state = G.move_frog(state, 0, +1)
                        else:
                            new_state = state
                        if new_state is not state:
                            state = new_state
                            dirty = True

                now = time.monotonic()
                if not paused and not show_help and not state.game_over and not state.won:
                    if now - last_tick >= TICK_INTERVAL:
                        new_state = G.tick(state)
                        last_tick = now
                        if new_state is not state:
                            state = new_state
                            dirty = True

        except KeyboardInterrupt:
            pass

    print(term.normal + "Thanks for playing Frogger!\n", end="")


if __name__ == "__main__":
    run()

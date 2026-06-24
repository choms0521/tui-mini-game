"""Entry point: terminal setup, keyboard input, and the main game loop.

Run with ``python main.py`` (or via the launcher). Both light cycles advance on
a fixed timer; the loop polls for a key with a short timeout so the player can
steer between ticks while the world keeps moving. All game logic lives in
game.py; this module only translates keystrokes and drives the clock.
"""
from __future__ import annotations

import random
import time

from blessed import Terminal

import board as B
import game as G
import render as R

POLL_TIMEOUT = 0.02  # seconds inkey waits before returning empty


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


def _apply_direction(state: G.GameState, action: str) -> G.GameState:
    """Map a direction action name to a set_player_dir() call."""
    mapping = {
        "up":    B.UP,
        "down":  B.DOWN,
        "left":  B.LEFT,
        "right": B.RIGHT,
    }
    new_dir = mapping.get(action)
    if new_dir is None:
        return state
    return G.set_player_dir(state, new_dir)


def run() -> None:
    term = Terminal()
    rng = random.Random()
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
                    if action == "help":
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
                    elif action in ("up", "down", "left", "right") and not show_help:
                        new_state = _apply_direction(state, action)
                        if new_state is not state:
                            state = new_state
                            dirty = True

                now = time.monotonic()
                if not paused and not show_help and not state.game_over:
                    if now - last_tick >= G.TICK_INTERVAL:
                        state = G.ai_tick(state, rng)
                        last_tick = now
                        dirty = True
        except KeyboardInterrupt:
            pass

    print(term.normal + "Thanks for playing Tron!\n", end="")


if __name__ == "__main__":
    run()

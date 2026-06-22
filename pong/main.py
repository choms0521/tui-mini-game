"""Entry point: terminal setup, keyboard input, and the Pong game loop.

Run with ``python main.py``. The paddles respond to input immediately while
the ball advances on a fixed timer, like breakout/main.py.
"""
from __future__ import annotations

import random
import time

from blessed import Terminal

import config as C
import game as G
import render as R

POLL_TIMEOUT = 0.02  # seconds inkey waits before returning empty


def _map_key(key) -> str | None:
    """Translate a blessed keystroke into a game action name."""
    if key.name == "KEY_UP":
        return "up"
    if key.name == "KEY_DOWN":
        return "down"
    char = str(key).lower()
    return {
        "w": "up",
        "s": "down",
        "q": "quit",
        " ": "space",
        "r": "restart",
    }.get(char)


def _warn_if_small(term: Terminal) -> None:
    need_w = R.BOARD_X + C.PLAY_W + 2 + R.PANEL_GAP + R.PANEL_WIDTH
    need_h = R.BOARD_Y + C.PLAY_H + 3
    if term.width < need_w or term.height < need_h:
        print(
            f"Note: terminal is {term.width}x{term.height}; "
            f"at least {need_w}x{need_h} is recommended for a clean layout."
        )
        print("Resize if the board looks cramped, then press a key to continue...")
        with term.cbreak():
            term.inkey()


def run() -> None:
    term = Terminal()
    _warn_if_small(term)

    rng = random.Random()
    state = G.new_game(rng)
    dirty = True
    last_tick = time.monotonic()

    with term.fullscreen(), term.cbreak(), term.hidden_cursor():
        print(term.home + term.clear, end="", flush=True)
        try:
            while True:
                if dirty:
                    R.draw(term, state)
                    dirty = False

                key = term.inkey(timeout=POLL_TIMEOUT)
                if key:
                    action = _map_key(key)
                    if action == "quit":
                        break
                    elif action == "restart":
                        state = G.new_game(rng)
                        last_tick = time.monotonic()
                        dirty = True
                    elif action == "space":
                        if not state.started and not state.game_over:
                            state = G.start(state)
                            last_tick = time.monotonic()
                            dirty = True
                        elif not state.game_over:
                            state = G.toggle_pause(state)
                            last_tick = time.monotonic()
                            dirty = True
                    elif action == "up" and not state.paused and not state.game_over:
                        state = G.move_player(state, -C.PADDLE_STEP)
                        dirty = True
                    elif action == "down" and not state.paused and not state.game_over:
                        state = G.move_player(state, C.PADDLE_STEP)
                        dirty = True

                now = time.monotonic()
                if state.started and not state.paused and not state.game_over:
                    if now - last_tick >= C.BALL_TICK:
                        state = G.tick(state, rng)
                        last_tick = now
                        dirty = True

        except KeyboardInterrupt:
            pass

    print(term.normal + "Thanks for playing Pong!\n", end="")


if __name__ == "__main__":
    run()

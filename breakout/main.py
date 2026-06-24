"""Entry point: terminal setup, keyboard input, and the Breakout game loop.

Run with ``python main.py`` (or the bundled ``run.sh``). Paddle moves respond to
input immediately, while the ball advances on a level-scaled timer.
"""
from __future__ import annotations

import time

from blessed import Terminal

import config as C
import game as G
import render as R

POLL_TIMEOUT = 0.02  # how long inkey waits before returning empty


def tick_interval(level: int) -> float:
    """Seconds between ball steps for the given level."""
    return max(C.MIN_TICK, C.BASE_TICK - (level - 1) * C.LEVEL_SPEEDUP)


def _map_key(key) -> str | None:
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
        " ": "launch",
        "r": "restart",
        "a": "left",
        "d": "right",
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
                    elif action and not paused and not show_help and not state.game_over:
                        if action == "left":
                            state = G.move_paddle(state, -C.PADDLE_STEP)
                        elif action == "right":
                            state = G.move_paddle(state, C.PADDLE_STEP)
                        elif action == "launch":
                            state = G.launch(state)
                        dirty = True

                now = time.monotonic()
                if not paused and not show_help and not state.game_over and state.launched:
                    if now - last_tick >= tick_interval(state.level):
                        state = G.tick(state)
                        last_tick = now
                        dirty = True
        except KeyboardInterrupt:
            pass

    print(term.normal + "Thanks for playing Breakout!\n", end="")


if __name__ == "__main__":
    run()

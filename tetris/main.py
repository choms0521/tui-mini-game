"""Entry point: terminal setup, keyboard input, and the main game loop.

Run with ``python main.py`` (or the bundled ``run.sh``). The loop polls for a
key with a short timeout so gravity keeps advancing even while no key is held.
"""
from __future__ import annotations

import random
import time

from blessed import Terminal

import board as B
import game as G
import render as R

BASE_FALL = 0.8       # seconds per gravity step at level 1
MIN_FALL = 0.05       # fastest possible step at high levels
LEVEL_STEP = 0.07     # how much each level shortens the step
POLL_TIMEOUT = 0.02   # how long inkey waits before returning empty


def fall_interval(level: int) -> float:
    """Seconds between gravity steps for the given level."""
    return max(MIN_FALL, BASE_FALL - (level - 1) * LEVEL_STEP)


def _map_key(key) -> str | None:
    """Translate a blessed keystroke into a game action name."""
    if key.name == "KEY_LEFT":
        return "left"
    if key.name == "KEY_RIGHT":
        return "right"
    if key.name == "KEY_DOWN":
        return "soft_drop"
    if key.name == "KEY_UP":
        return "rotate_cw"

    char = str(key).lower()
    return {
        "q": "quit",
        "p": "pause",
        " ": "hard_drop",
        "x": "rotate_cw",
        "z": "rotate_ccw",
        "r": "restart",
    }.get(char)


def _apply(state: G.GameState, action: str, rng: random.Random) -> G.GameState:
    """Apply a movement/rotation action and return the resulting state."""
    if action == "left":
        return G.try_move(state, 0, -1)
    if action == "right":
        return G.try_move(state, 0, 1)
    if action == "soft_drop":
        return G.step_down(state, rng)
    if action == "rotate_cw":
        return G.try_rotate(state, clockwise=True)
    if action == "rotate_ccw":
        return G.try_rotate(state, clockwise=False)
    if action == "hard_drop":
        return G.hard_drop(state, rng)
    return state


def _warn_if_small(term: Terminal) -> None:
    need_w = R.BOARD_X + R._CELL_WIDTH + R.PANEL_GAP + R.PANEL_WIDTH
    need_h = R.BOARD_Y + B.HEIGHT + 3
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
    paused = False
    dirty = True
    last_fall = time.monotonic()

    with term.fullscreen(), term.cbreak(), term.hidden_cursor():
        print(term.home + term.clear, end="", flush=True)
        try:
            while True:
                if dirty:
                    R.draw(term, state, paused=paused)
                    dirty = False

                key = term.inkey(timeout=POLL_TIMEOUT)
                if key:
                    action = _map_key(key)
                    if action == "quit":
                        break
                    if action == "pause":
                        paused = not paused
                        last_fall = time.monotonic()
                        dirty = True
                    elif action == "restart" and state.game_over:
                        state = G.new_game(rng)
                        paused = False
                        last_fall = time.monotonic()
                        dirty = True
                    elif action and not paused and not state.game_over:
                        new_state = _apply(state, action, rng)
                        if new_state is not state:
                            state = new_state
                            dirty = True
                        if action == "hard_drop":
                            last_fall = time.monotonic()

                now = time.monotonic()
                if not paused and not state.game_over:
                    if now - last_fall >= fall_interval(state.level):
                        state = G.step_down(state, rng)
                        last_fall = now
                        dirty = True
        except KeyboardInterrupt:
            pass

    print(term.normal + "Thanks for playing Tetris!\n", end="")


if __name__ == "__main__":
    run()

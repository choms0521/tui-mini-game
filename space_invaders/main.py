"""Entry point: terminal setup, keyboard input, and the main game loop.

Run with ``python main.py``. The loop polls for a key with a short timeout so
the fleet and bullets keep advancing even while no key is held.
"""
from __future__ import annotations

import random
import time

from blessed import Terminal

import game as G
import render as R

# Seconds between bullet advancement ticks.
BULLET_INTERVAL = 0.08

# Fleet tick interval at full strength; shrinks as aliens are destroyed.
FLEET_BASE = 0.6
FLEET_MIN = 0.12

# How long inkey() waits before returning an empty keystroke.
POLL_TIMEOUT = 0.02


def fleet_interval(remaining: int, total: int) -> float:
    """Return fleet tick seconds; speeds up as aliens are destroyed."""
    if total == 0:
        return FLEET_MIN
    ratio = remaining / total
    return max(FLEET_MIN, FLEET_BASE * ratio)


def _map_key(key) -> str | None:
    """Translate a blessed keystroke into a game action name."""
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
        " ": "fire",
        "r": "restart",
    }.get(char)


def run() -> None:
    term = Terminal()
    rng = random.Random()
    state = G.new_game(rng)
    total_aliens = len(state.aliens)
    paused = False
    show_help = False
    dirty = True

    now = time.monotonic()
    last_bullet = now
    last_fleet = now

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
                        now = time.monotonic()
                        last_bullet = now
                        last_fleet = now
                        dirty = True
                    elif action == "pause":
                        paused = not paused
                        now = time.monotonic()
                        last_bullet = now
                        last_fleet = now
                        dirty = True
                    elif action == "restart":
                        state = G.new_game(rng)
                        total_aliens = len(state.aliens)
                        paused = False
                        show_help = False
                        now = time.monotonic()
                        last_bullet = now
                        last_fleet = now
                        dirty = True
                    elif action and not paused and not show_help and not state.game_over and not state.won:
                        if action == "left":
                            new_state = G.move_player(state, -1)
                        elif action == "right":
                            new_state = G.move_player(state, 1)
                        elif action == "fire":
                            new_state = G.fire(state)
                        else:
                            new_state = state
                        if new_state is not state:
                            state = new_state
                            dirty = True

                now = time.monotonic()
                if not paused and not show_help and not state.game_over and not state.won:
                    if now - last_bullet >= BULLET_INTERVAL:
                        new_state = G.advance_bullets(state)
                        last_bullet = now
                        if new_state is not state:
                            state = new_state
                            dirty = True

                    fi = fleet_interval(len(state.aliens), total_aliens)
                    if now - last_fleet >= fi:
                        new_state = G.advance_fleet(state)
                        last_fleet = now
                        if new_state is not state:
                            state = new_state
                            dirty = True
        except KeyboardInterrupt:
            pass

    print(term.normal + "Thanks for playing Space Invaders!\n", end="")


if __name__ == "__main__":
    run()

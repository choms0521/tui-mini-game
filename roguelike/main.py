"""Entry point: terminal setup, keyboard input, and the main game loop.

Run with ``python main.py`` (or via the launcher).  The loop blocks on
``term.inkey`` with a short timeout so the UI stays responsive without
burning CPU.  The world only advances when the player presses a movement
key — this is a turn-based game, not tick-based.
"""
from __future__ import annotations

import random

from blessed import Terminal

import dungeon as D
import game as G
import render as R

POLL_TIMEOUT = 0.05  # seconds; short enough to feel instant


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
        "r": "restart",
        "q": "quit",
        "h": "help",
        "?": "help",
    }.get(char)


def run() -> None:
    """Run the roguelike; returns when the player presses q."""
    term = Terminal()
    rng = random.Random()
    state = G.new_game(rng)
    show_help = False
    dirty = True

    with term.fullscreen(), term.cbreak(), term.hidden_cursor():
        print(term.home + term.clear, end="", flush=True)
        try:
            while True:
                if dirty:
                    R.draw(term, state, show_help=show_help)
                    dirty = False

                key = term.inkey(timeout=POLL_TIMEOUT)
                if not key:
                    continue

                action = _map_key(key)
                if action == "quit":
                    break
                elif action == "help":
                    show_help = not show_help
                    dirty = True
                elif action == "restart" and state.game_over:
                    state = G.restart(rng)
                    show_help = False
                    dirty = True
                elif not state.game_over and not show_help:
                    dcol, drow = 0, 0
                    if action == "up":
                        drow = -1
                    elif action == "down":
                        drow = 1
                    elif action == "left":
                        dcol = -1
                    elif action == "right":
                        dcol = 1

                    if dcol != 0 or drow != 0:
                        # Check for stair descent before moving.
                        p = state.player
                        target_col = p.col + dcol
                        target_row = p.row + drow
                        if (
                            0 <= target_row < len(state.grid)
                            and 0 <= target_col < len(state.grid[0])
                            and state.grid[target_row][target_col] == D.STAIRS
                        ):
                            state = G.descend(state, rng)
                            dirty = True
                        else:
                            new_state = G.step(state, dcol, drow, rng)
                            if new_state is not state:
                                state = new_state
                                dirty = True
        except KeyboardInterrupt:
            pass

    print(term.normal + "Thanks for playing Roguelike!\n", end="")


if __name__ == "__main__":
    run()

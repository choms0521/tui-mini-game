"""Compose the launcher menu as printable strings (truecolor, flicker-free).

Mirrors the bundled games: build the whole frame as one string and print it
after moving the cursor home, padding every line to a fixed width so a shorter
line never leaves stale characters behind. The string builders are pure so the
self-test can exercise them without a TTY.
"""
from __future__ import annotations

from typing import List, Optional, Sequence

from blessed import Terminal

TITLE = "mini-game"
SUBTITLE = "terminal game launcher"

MENU_X = 4
MENU_Y = 2
MENU_WIDTH = 52


def _pad(term: Terminal, text: str, width: int = MENU_WIDTH) -> str:
    """Right-pad to a fixed printable width, ignoring colour escape codes."""
    extra = width - term.length(text)
    return text + " " * extra if extra > 0 else text


def menu_lines(term: Terminal, games: Sequence, selected: int) -> List[str]:
    """Build the menu as a list of (already coloured) lines."""
    accent = term.color_rgb(0, 220, 200)
    dim = term.color_rgb(120, 120, 120)

    lines = [term.bold(accent(TITLE)), dim(SUBTITLE), ""]
    if games:
        for i, game in enumerate(games):
            if i == selected:
                lines.append(accent(" > ") + term.bold(game.name))
            else:
                lines.append("   " + game.name)
        lines.append("")
        lines.append(dim(games[selected].description))
    else:
        lines.append(dim("no games found next to the launcher"))

    lines.extend(
        [
            "",
            dim("up/down  select"),
            dim("enter    play"),
            dim("q        quit"),
        ]
    )
    return lines


def draw(
    term: Terminal,
    games: Sequence,
    selected: int,
    message: Optional[str] = None,
) -> None:
    """Render the whole menu frame in one print call."""
    lines = menu_lines(term, games, selected)
    frame = [term.home]
    for i, line in enumerate(lines):
        frame.append(term.move_xy(MENU_X, MENU_Y + i) + _pad(term, line))

    # Always paint the message row (padded) so a cleared message leaves no trail.
    text = term.color_rgb(240, 120, 40)(message) if message else ""
    frame.append(term.move_xy(MENU_X, MENU_Y + len(lines) + 1) + _pad(term, text))

    print("".join(frame), end="", flush=True)

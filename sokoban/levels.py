"""Hand-designed Sokoban levels.

Each level is encoded as a list of strings using the standard Sokoban notation:
    '#'  wall
    '@'  player starting position
    '$'  box
    '.'  goal
    '*'  box on goal
    '+'  player on goal
    ' '  floor

All levels are fully wall-enclosed so no out-of-bounds tile is reachable.
"""
from __future__ import annotations

from typing import List, Tuple

# Each entry is a list of ASCII rows.
LEVELS: List[List[str]] = [
    # Level 0 — introductory: one box, one goal
    [
        "#######",
        "#     #",
        "#  $  #",
        "#  .  #",
        "#  @  #",
        "#     #",
        "#######",
    ],
    # Level 1 — two boxes, two goals in a corridor
    [
        "#########",
        "#   .   #",
        "#   $   #",
        "#   @   #",
        "#   $   #",
        "#   .   #",
        "#########",
    ],
    # Level 2 — three boxes, goals in corners
    [
        "##########",
        "#.  .  .##",
        "# $  $  ##",
        "#  $    ##",
        "#  @    ##",
        "#       ##",
        "##########",
    ],
    # Level 3 — boxes travel to scattered goals (3 boxes, 3 goals)
    [
        "#########",
        "#       #",
        "#  $    #",
        "#  .    #",
        "#  $ .  #",
        "#  @    #",
        "#  $ .  #",
        "#########",
    ],
    # Level 4 — larger board with more moves required
    [
        "##########",
        "#        #",
        "# .$.$.$ #",
        "#        #",
        "# $.$.$. #",
        "#        #",
        "#   @    #",
        "##########",
    ],
]

# Global maximum dimensions across all levels — used by render to pad
# every frame to the same size so no stale characters remain on level transitions.
MAX_WIDTH: int = max(len(row) for level in LEVELS for row in level)
MAX_HEIGHT: int = max(len(level) for level in LEVELS)


def parse_level(
    index: int,
) -> Tuple[
    frozenset,  # walls: frozenset of (row, col)
    frozenset,  # goals: frozenset of (row, col)
    frozenset,  # boxes: frozenset of (row, col)
    Tuple[int, int],  # player: (row, col)
    int,  # level_width
    int,  # level_height
]:
    """Parse level *index* into static (walls, goals) and dynamic (boxes, player).

    Returns a 6-tuple:
        walls       — frozenset of (row, col) pairs that are impassable
        goals       — frozenset of (row, col) pairs that are goal squares
        boxes       — frozenset of initial box positions
        player      — (row, col) of the player's starting position
        width       — column count of the widest row
        height      — row count of the level
    """
    rows = LEVELS[index]
    walls: set = set()
    goals: set = set()
    boxes: set = set()
    player: Tuple[int, int] | None = None

    for r, row in enumerate(rows):
        for c, ch in enumerate(row):
            if ch == "#":
                walls.add((r, c))
            elif ch == ".":
                goals.add((r, c))
            elif ch == "$":
                boxes.add((r, c))
            elif ch == "*":
                goals.add((r, c))
                boxes.add((r, c))
            elif ch == "@":
                player = (r, c)
            elif ch == "+":
                goals.add((r, c))
                player = (r, c)

    if player is None:
        raise ValueError(f"Level {index} has no player start position")

    height = len(rows)
    width = max(len(row) for row in rows)

    return (
        frozenset(walls),
        frozenset(goals),
        frozenset(boxes),
        player,
        width,
        height,
    )

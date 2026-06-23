"""Field dimensions and lane configuration for Frogger.

Provides grid constants and the lane definitions that describe the playfield.
All values here are pure data: no game logic, no blessed imports.
"""
from __future__ import annotations

from typing import NamedTuple, Tuple

# Playfield dimensions (characters).
WIDTH = 40    # number of columns
# Lane count: 1 goal + 3 river + 1 safe (mid) + 3 road + 1 safe (start) = 9
HEIGHT = 9    # number of rows; row 0 = goal row, row HEIGHT-1 = start safe row

START_ROW = HEIGHT - 1  # frog begins here
GOAL_ROW = 0            # reaching this row lands in a goal slot

# Goal slots: column indices of the valid landing pads.
GOAL_COLS: Tuple[int, ...] = (4, 12, 20, 28, 36)
NUM_GOALS = len(GOAL_COLS)

# Score awarded when the frog reaches an empty goal slot.
SCORE_PER_GOAL = 50

# Starting lives.
INITIAL_LIVES = 3

# Frog starting column (centred).
START_COL = WIDTH // 2


class LaneDef(NamedTuple):
    """Static definition of a single lane."""
    kind: str               # "safe" | "road" | "river"
    direction: int          # +1 = right, -1 = left; 0 for safe lanes
    speed: int              # cells per tick
    pattern: Tuple[int, ...]  # obstacle start columns (width-relative)
    span: int               # obstacle length in cells (car or log width)


# ---------------------------------------------------------------------------
# Lane layout: index 0 = goal row (top), index HEIGHT-1 = start row (bottom).
# Obstacles in "road" lanes are cars; in "river" lanes are logs.
# "safe" lanes have no obstacles.
# ---------------------------------------------------------------------------
LANES: Tuple[LaneDef, ...] = (
    # row 0 — goal row (treated as "safe"; goal logic is handled in game.py)
    LaneDef(kind="safe",  direction= 0, speed=0, pattern=(),        span=0),
    # row 1 — river (fast, rightward logs)
    LaneDef(kind="river", direction=+1, speed=2, pattern=(0, 14, 28), span=6),
    # row 2 — river (medium, leftward logs)
    LaneDef(kind="river", direction=-1, speed=1, pattern=(5, 20, 35), span=5),
    # row 3 — river (slow, rightward logs)
    LaneDef(kind="river", direction=+1, speed=1, pattern=(2, 18, 32), span=7),
    # row 4 — safe middle strip
    LaneDef(kind="safe",  direction= 0, speed=0, pattern=(),        span=0),
    # row 5 — road (fast cars, leftward)
    LaneDef(kind="road",  direction=-1, speed=2, pattern=(3, 18, 33), span=3),
    # row 6 — road (medium cars, rightward)
    LaneDef(kind="road",  direction=+1, speed=1, pattern=(0, 15, 28), span=4),
    # row 7 — road (slow cars, leftward)
    LaneDef(kind="road",  direction=-1, speed=1, pattern=(8, 24, 36), span=3),
    # row 8 — start safe zone
    LaneDef(kind="safe",  direction= 0, speed=0, pattern=(),        span=0),
)

assert len(LANES) == HEIGHT, "LANES length must equal HEIGHT"


def in_bounds(row: int, col: int) -> bool:
    """True when (row, col) is within the playfield."""
    return 0 <= row < HEIGHT and 0 <= col < WIDTH


def obstacle_cells(lane: LaneDef, offset: int) -> frozenset:
    """Return the set of columns occupied by obstacles in *lane* at *offset*.

    The offset is a cumulative scroll accumulator; the actual obstacle positions
    are derived deterministically: each obstacle start shifts by `offset` and
    wraps around WIDTH, then the span fills contiguous columns (also wrapping).
    """
    if not lane.pattern:
        return frozenset()
    cols: set[int] = set()
    for start in lane.pattern:
        base = (start + offset) % WIDTH
        for k in range(lane.span):
            cols.add((base + k) % WIDTH)
    return frozenset(cols)

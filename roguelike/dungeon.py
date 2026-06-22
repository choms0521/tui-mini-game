"""Procedural dungeon generation: rooms, corridors, and tile placement.

All map data is stored as an immutable tuple-of-tuples grid.  Entity positions
(player, monsters, items) live in ``game.py`` state, not burned into the tiles
here.  This keeps dungeon generation free of entity logic and makes it easy to
rebuild a fresh level on descent.
"""
from __future__ import annotations

import random
from dataclasses import dataclass
from typing import List, Tuple

# Tile constants
WALL = "#"
FLOOR = "."
STAIRS = ">"

Grid = Tuple[Tuple[str, ...], ...]

# Dungeon dimensions
WIDTH = 40
HEIGHT = 22

# Generation parameters
MIN_ROOMS = 5
MAX_ROOMS = 8
ROOM_MIN = 4
ROOM_MAX = 8


@dataclass(frozen=True)
class Room:
    """A rectangular room defined by its top-left corner and size."""

    x: int
    y: int
    w: int
    h: int

    @property
    def center(self) -> Tuple[int, int]:
        """(col, row) center of the room."""
        return (self.x + self.w // 2, self.y + self.h // 2)

    def inner_tiles(self) -> List[Tuple[int, int]]:
        """All (col, row) floor tiles inside the room (excluding walls)."""
        return [
            (cx, ry)
            for ry in range(self.y + 1, self.y + self.h - 1)
            for cx in range(self.x + 1, self.x + self.w - 1)
        ]

    def overlaps(self, other: "Room") -> bool:
        """True if this room's bounding box (plus 1 tile margin) overlaps another."""
        return (
            self.x <= other.x + other.w
            and self.x + self.w >= other.x
            and self.y <= other.y + other.h
            and self.y + self.h >= other.y
        )


def _carve_room(rows: List[List[str]], room: Room) -> None:
    """Carve floor tiles into ``rows`` for the given room (mutable helper)."""
    for ry in range(room.y + 1, room.y + room.h - 1):
        for cx in range(room.x + 1, room.x + room.w - 1):
            rows[ry][cx] = FLOOR


def _carve_h_corridor(rows: List[List[str]], x1: int, x2: int, y: int) -> None:
    """Carve a horizontal corridor segment (mutable helper)."""
    for cx in range(min(x1, x2), max(x1, x2) + 1):
        rows[y][cx] = FLOOR


def _carve_v_corridor(rows: List[List[str]], y1: int, y2: int, x: int) -> None:
    """Carve a vertical corridor segment (mutable helper)."""
    for ry in range(min(y1, y2), max(y1, y2) + 1):
        rows[ry][x] = FLOOR


def _connect_rooms(rows: List[List[str]], a: Room, b: Room, rng: random.Random) -> None:
    """Connect two rooms with an L-shaped corridor."""
    ax, ay = a.center
    bx, by = b.center
    # Randomly choose whether to go horizontal-first or vertical-first.
    if rng.random() < 0.5:
        _carve_h_corridor(rows, ax, bx, ay)
        _carve_v_corridor(rows, ay, by, bx)
    else:
        _carve_v_corridor(rows, ay, by, ax)
        _carve_h_corridor(rows, ax, bx, by)


def generate(rng: random.Random) -> Tuple[Grid, List[Room]]:
    """Generate a walled dungeon grid and return ``(grid, rooms)``.

    Rooms are connected consecutively so every room is reachable.
    The caller places entities using the returned room list.
    """
    rows: List[List[str]] = [[WALL] * WIDTH for _ in range(HEIGHT)]
    rooms: List[Room] = []

    attempts = 0
    max_attempts = 200
    target = rng.randint(MIN_ROOMS, MAX_ROOMS)

    while len(rooms) < target and attempts < max_attempts:
        attempts += 1
        w = rng.randint(ROOM_MIN, ROOM_MAX)
        h = rng.randint(ROOM_MIN, ROOM_MAX)
        x = rng.randint(1, WIDTH - w - 1)
        y = rng.randint(1, HEIGHT - h - 1)
        candidate = Room(x=x, y=y, w=w, h=h)

        if any(candidate.overlaps(r) for r in rooms):
            continue

        _carve_room(rows, candidate)
        if rooms:
            _connect_rooms(rows, rooms[-1], candidate, rng)
        rooms.append(candidate)

    # Freeze to immutable.
    grid: Grid = tuple(tuple(row) for row in rows)
    return grid, rooms


def place_stairs(grid: Grid, col: int, row: int) -> Grid:
    """Return a new grid with the stairs glyph placed at (col, row)."""
    rows = [list(r) for r in grid]
    rows[row][col] = STAIRS
    return tuple(tuple(r) for r in rows)


def all_floor_tiles(grid: Grid) -> List[Tuple[int, int]]:
    """Return all (col, row) positions that are floor tiles."""
    return [
        (c, r)
        for r in range(len(grid))
        for c in range(len(grid[r]))
        if grid[r][c] == FLOOR
    ]

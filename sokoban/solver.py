"""Standalone Sokoban solvability checker (BFS over (player, boxes) states).

Used only as a development/verification tool — not shipped with the game.
"""
from __future__ import annotations

from collections import deque
from typing import FrozenSet, List, Optional, Tuple

Pos = Tuple[int, int]
DIRS = [(-1, 0), (1, 0), (0, -1), (0, 1)]


def parse(rows: List[str]):
    walls, goals, boxes = set(), set(), set()
    player: Optional[Pos] = None
    for r, row in enumerate(rows):
        for c, ch in enumerate(row):
            p = (r, c)
            if ch == "#":
                walls.add(p)
            elif ch == ".":
                goals.add(p)
            elif ch == "$":
                boxes.add(p)
            elif ch == "*":
                goals.add(p); boxes.add(p)
            elif ch == "@":
                player = p
            elif ch == "+":
                goals.add(p); player = p
    return frozenset(walls), frozenset(goals), frozenset(boxes), player


def _dead_corner(walls: FrozenSet[Pos], goals: FrozenSet[Pos]) -> set:
    """Simple corner deadlock squares: a non-goal floor wedged in a corner."""
    dead = set()
    rows = max(r for r, _ in walls) + 1
    cols = max(c for _, c in walls) + 1
    for r in range(rows):
        for c in range(cols):
            p = (r, c)
            if p in walls or p in goals:
                continue
            up = (r - 1, c) in walls
            down = (r + 1, c) in walls
            left = (r, c - 1) in walls
            right = (r, c + 1) in walls
            if (up or down) and (left or right):
                dead.add(p)
    return dead


def _reachable(player: Pos, walls: FrozenSet[Pos], boxes: FrozenSet[Pos]) -> set:
    """All squares the player can walk to without pushing any box."""
    seen = {player}
    stack = [player]
    while stack:
        r, c = stack.pop()
        for dr, dc in DIRS:
            n = (r + dr, c + dc)
            if n in walls or n in boxes or n in seen:
                continue
            seen.add(n)
            stack.append(n)
    return seen


def solve(rows: List[str], max_states: int = 5_000_000):
    """Push-based BFS with player-region normalization.

    A state is (frozenset(boxes), normalized_player) where normalized_player is
    the lexicographically smallest square the player can reach.  Transitions are
    box pushes only, which collapses the huge walk-step state space.
    Returns the minimum number of box pushes, or False if unsolvable.
    """
    walls, goals, boxes, player = parse(rows)
    if player is None:
        return None  # malformed
    dead = _dead_corner(walls, goals)

    def norm(p: Pos, bxs: FrozenSet[Pos]) -> Pos:
        return min(_reachable(p, walls, bxs))

    start_norm = norm(player, boxes)
    seen = {(boxes, start_norm)}
    q = deque([(player, boxes, 0)])
    states = 0
    while q:
        player, boxes, pushes = q.popleft()
        if boxes >= goals:
            return pushes
        states += 1
        if states > max_states:
            return -1  # gave up (treat as unknown)
        region = _reachable(player, walls, boxes)
        for box in boxes:
            br, bc = box
            for dr, dc in DIRS:
                stand = (br - dr, bc - dc)   # where the player must stand to push
                dest = (br + dr, bc + dc)    # where the box would land
                if stand not in region:
                    continue
                if dest in walls or dest in boxes or dest in dead:
                    continue
                new_boxes = (boxes - {box}) | {dest}
                key = (new_boxes, norm(box, new_boxes))
                if key not in seen:
                    seen.add(key)
                    q.append((box, new_boxes, pushes + 1))
    return False  # exhausted, no solution


if __name__ == "__main__":
    import levels as L
    for i, lv in enumerate(L.LEVELS):
        res = solve(lv)
        if res is False:
            verdict = "UNSOLVABLE"
        elif res == -1:
            verdict = "UNKNOWN (state cap hit)"
        elif res is None:
            verdict = "MALFORMED"
        else:
            verdict = f"solvable in {res} box-pushes"
        print(f"Level {i+1} (idx {i}): {verdict}")

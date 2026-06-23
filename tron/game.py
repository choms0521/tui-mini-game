"""Immutable game state and the pure transitions that drive a game of Tron.

Two light cycles (the player and the AI) advance one cell every tick in their
current direction, leaving a solid wall on every cell they vacate. The first to
enter a wall, the grid boundary, or the opponent's cell dies.

Every transition takes a GameState and returns a new one via dataclasses.replace,
so nothing is ever mutated in place and the game loop can compare object identity
to detect actual changes. The AI is deterministic given an injected random.Random,
and none of this module depends on blessed, so the whole core is headless-testable.
"""
from __future__ import annotations

import random
from dataclasses import dataclass, field, replace
from typing import FrozenSet, List, Optional, Tuple

import board as B

Pos = Tuple[int, int]
Direction = Tuple[int, int]

# Player identifiers (also used as winner values; 0 means a draw).
PLAYER = 1
AI = 2

# Tick speed: seconds between advances for both cycles.
TICK_INTERVAL = 0.09

# Upper bound on cells visited by the AI's flood-fill so the per-tick cost stays
# small even on a large open grid. The whole interior is the natural ceiling.
_FLOOD_CAP = B.WIDTH * B.HEIGHT


@dataclass(frozen=True)
class GameState:
    """Complete, immutable snapshot of one Tron game.

    walls        -- every trail cell left behind by either cycle.
    player_pos   -- the player cycle's head (row, col).
    player_dir   -- the player's current direction as (drow, dcol).
    ai_pos       -- the AI cycle's head (row, col).
    ai_dir       -- the AI's current direction as (drow, dcol).
    player_alive -- False once the player has crashed.
    ai_alive     -- False once the AI has crashed.
    game_over    -- True once at least one cycle has crashed.
    winner       -- PLAYER, AI, 0 for a draw, or None while play continues.
    tick         -- number of ticks elapsed since the game began.
    player_trail -- render-only set of the player's vacated cells.
    ai_trail     -- render-only set of the AI's vacated cells.

    walls is the single source of truth for collisions (player_trail and ai_trail
    together equal walls); the per-owner trails exist only so the renderer can
    paint each cycle's wall in its own color.
    """

    walls: FrozenSet[Pos]
    player_pos: Pos
    player_dir: Direction
    ai_pos: Pos
    ai_dir: Direction
    player_alive: bool = True
    ai_alive: bool = True
    game_over: bool = False
    winner: Optional[int] = None
    tick: int = 0
    player_trail: FrozenSet[Pos] = field(default_factory=frozenset)
    ai_trail: FrozenSet[Pos] = field(default_factory=frozenset)


def new_game() -> GameState:
    """Create a fresh game with the two cycles facing each other.

    The player starts on the left quarter heading right; the AI starts on the
    right quarter heading left. No trails exist yet.
    """
    row = B.HEIGHT // 2
    player_pos = (row, B.WIDTH // 4)
    ai_pos = (row, B.WIDTH - 1 - B.WIDTH // 4)
    return GameState(
        walls=frozenset(),
        player_pos=player_pos,
        player_dir=B.RIGHT,
        ai_pos=ai_pos,
        ai_dir=B.LEFT,
    )


def _is_reverse(current: Direction, new_dir: Direction) -> bool:
    """True when *new_dir* is a 180-degree reversal of *current*."""
    return new_dir == (-current[0], -current[1])


def set_player_dir(state: GameState, new_dir: Direction) -> GameState:
    """Request a player direction change; ignores 180-degree reversals.

    Returns the same state object when the turn is illegal (game over, an
    unknown vector, or a direct reversal) so the caller can tell nothing changed.
    """
    if state.game_over or new_dir not in B.DIRECTIONS:
        return state
    if _is_reverse(state.player_dir, new_dir):
        return state
    return replace(state, player_dir=new_dir)


def tick(state: GameState) -> GameState:
    """Advance both living cycles one cell and resolve all collisions.

    Ordering (locked so the four collision cases fall out cleanly):
      1. Compute each cycle's next cell from its current direction.
      2. Add both vacated head cells to the wall set *before* any membership
         test. This is what makes a position swap fatal: each cycle's target is
         the other's just-vacated cell, which is now a wall.
      3. A head-on (both targeting the same cell) is detected explicitly on top.
      4. A cycle dies if its target is out of bounds, lands on a wall, or is a
         head-on. Deaths set the alive flags, which decide game_over / winner.

    Returns the same state object when the game is already over.
    """
    if state.game_over:
        return state

    p_pos = state.player_pos
    a_pos = state.ai_pos

    p_next = B.add(p_pos, state.player_dir) if state.player_alive else p_pos
    a_next = B.add(a_pos, state.ai_dir) if state.ai_alive else a_pos

    # Both vacated cells become walls before any collision test (handles swap).
    new_walls = state.walls
    new_player_trail = state.player_trail
    new_ai_trail = state.ai_trail
    if state.player_alive:
        new_walls = new_walls | {p_pos}
        new_player_trail = new_player_trail | {p_pos}
    if state.ai_alive:
        new_walls = new_walls | {a_pos}
        new_ai_trail = new_ai_trail | {a_pos}

    head_on = state.player_alive and state.ai_alive and p_next == a_next

    player_dead = False
    if state.player_alive:
        player_dead = (
            not B.in_bounds(*p_next)
            or p_next in new_walls
            or head_on
        )

    ai_dead = False
    if state.ai_alive:
        ai_dead = (
            not B.in_bounds(*a_next)
            or a_next in new_walls
            or head_on
        )

    player_alive = state.player_alive and not player_dead
    ai_alive = state.ai_alive and not ai_dead

    # A dead cycle does not move onto a fatal cell; it stays where it crashed.
    final_player_pos = p_next if player_alive else p_pos
    final_ai_pos = a_next if ai_alive else a_pos

    game_over = not (player_alive and ai_alive)
    winner: Optional[int] = None
    if game_over:
        if player_alive and not ai_alive:
            winner = PLAYER
        elif ai_alive and not player_alive:
            winner = AI
        else:
            winner = 0  # both dead -> draw

    return replace(
        state,
        walls=new_walls,
        player_pos=final_player_pos,
        ai_pos=final_ai_pos,
        player_alive=player_alive,
        ai_alive=ai_alive,
        game_over=game_over,
        winner=winner,
        tick=state.tick + 1,
        player_trail=new_player_trail,
        ai_trail=new_ai_trail,
    )


# ---------------------------------------------------------------------------
# Opponent AI: avoidance via bounded flood-fill of reachable open space
# ---------------------------------------------------------------------------

def _candidate_dirs(current: Direction) -> List[Direction]:
    """The non-reversing directions, in a fixed order for determinism."""
    return [d for d in B.DIRECTIONS if not _is_reverse(current, d)]


def _is_fatal(next_cell: Pos, blocked: FrozenSet[Pos], opp_pos: Pos) -> bool:
    """Mirror tick's death rule for a single candidate next cell.

    *blocked* is the set of cells the AI cannot enter (current walls plus the
    opponent's just-vacated cell, since both cycles move on the same tick).
    Entering the opponent's next cell (*opp_pos* here) is a head-on collision.
    """
    return (
        not B.in_bounds(*next_cell)
        or next_cell in blocked
        or next_cell == opp_pos
    )


def _flood_area(start: Pos, blocked: FrozenSet[Pos]) -> int:
    """Count cells reachable from *start* over 4-neighbors, bounded by a cap.

    *blocked* cells and out-of-bounds cells are not traversable. *start* itself
    is assumed to be a legal open cell and is counted.
    """
    seen = {start}
    stack = [start]
    while stack and len(seen) < _FLOOD_CAP:
        cell = stack.pop()
        for d in B.DIRECTIONS:
            nb = B.add(cell, d)
            if nb in seen:
                continue
            if not B.in_bounds(*nb) or nb in blocked:
                continue
            seen.add(nb)
            stack.append(nb)
    return len(seen)


def ai_choose_dir(state: GameState, rng: random.Random) -> Direction:
    """Return the direction the AI should take this tick.

    Among the non-reversing candidates, immediately fatal directions are
    discarded; among the survivors the one whose resulting next cell can reach
    the most open space (bounded flood-fill) is chosen. Ties are broken with the
    injected *rng* so the choice is deterministic for a seeded Random. When every
    candidate is fatal, a legal (non-reversing) direction is returned anyway.
    """
    candidates = _candidate_dirs(state.ai_dir)

    # Cells the AI may not enter this tick: existing walls plus both heads'
    # just-vacated cells (its own and the opponent's, which move simultaneously).
    blocked = state.walls | {state.ai_pos, state.player_pos}
    # The opponent's next cell is a head-on target.
    opp_next = B.add(state.player_pos, state.player_dir) if state.player_alive else state.player_pos

    safe: List[Tuple[int, Direction]] = []
    for d in candidates:
        nxt = B.add(state.ai_pos, d)
        if _is_fatal(nxt, blocked, opp_next):
            continue
        area = _flood_area(nxt, blocked)
        safe.append((area, d))

    if not safe:
        # Every direction is fatal; return any legal one (death is unavoidable).
        return rng.choice(candidates) if candidates else state.ai_dir

    best_area = max(area for area, _ in safe)
    best_dirs = [d for area, d in safe if area == best_area]
    return rng.choice(best_dirs)


def ai_tick(state: GameState, rng: random.Random) -> GameState:
    """Set the AI's direction via ai_choose_dir, then advance the world by one tick.

    Convenience wrapper for the main loop so the AI decision and the tick stay
    in game.py. The player's direction is whatever the input handler last set.
    """
    if state.game_over:
        return state
    chosen = ai_choose_dir(state, rng) if state.ai_alive else state.ai_dir
    return tick(replace(state, ai_dir=chosen))

"""Immutable game state and all turn-based transitions for the roguelike.

Every transition returns a new :class:`GameState` via ``dataclasses.replace``
so the main loop can compare object identity to detect changes.  Randomness is
injected as a ``random.Random`` instance — never via module-global ``random.*``
calls — so the selftest can run deterministically with a seeded RNG.
"""
from __future__ import annotations

import random
from dataclasses import dataclass, replace
from typing import Optional, Tuple

import dungeon as D

# Item kinds
POTION = "!"
GEAR = "/"

# Monster definitions: (glyph, base_hp, base_attack, display_name)
MONSTER_DEFS = {
    "r": (3, 1, "Rat"),
    "g": (6, 2, "Goblin"),
}

HEAL_AMOUNT = 5
GEAR_ATTACK_BONUS = 2

# How many monsters and items to place per level (base values).
MONSTERS_BASE = 3
ITEMS_BASE = 2


@dataclass(frozen=True)
class Monster:
    """A single monster on the current level."""

    col: int
    row: int
    glyph: str      # 'r' or 'g'
    hp: int
    attack: int


@dataclass(frozen=True)
class Item:
    """A floor item waiting to be picked up."""

    col: int
    row: int
    kind: str       # POTION or GEAR


@dataclass(frozen=True)
class Player:
    """The player character."""

    col: int
    row: int
    hp: int
    max_hp: int
    attack: int


@dataclass(frozen=True)
class GameState:
    """Complete, frozen snapshot of the game world."""

    grid: D.Grid
    player: Player
    monsters: Tuple[Monster, ...]
    items: Tuple[Item, ...]
    depth: int
    score: int
    game_over: bool


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _monster_at(monsters: Tuple[Monster, ...], col: int, row: int) -> Optional[Monster]:
    """Return the monster occupying (col, row), or None."""
    for m in monsters:
        if m.col == col and m.row == row:
            return m
    return None


def _item_at(items: Tuple[Item, ...], col: int, row: int) -> Optional[Item]:
    """Return the item at (col, row), or None."""
    for item in items:
        if item.col == col and item.row == row:
            return item
    return None


def _is_walkable(grid: D.Grid, col: int, row: int) -> bool:
    """True when the tile is floor or stairs (not a wall, not out of bounds)."""
    if row < 0 or row >= len(grid) or col < 0 or col >= len(grid[0]):
        return False
    return grid[row][col] != D.WALL


def _sample_distinct(tiles: list, n: int, rng: random.Random) -> list:
    """Return up to ``n`` distinct tiles chosen without replacement."""
    chosen: list = []
    pool = list(tiles)
    for _ in range(min(n, len(pool))):
        idx = rng.randrange(len(pool))
        chosen.append(pool.pop(idx))
    return chosen


# ---------------------------------------------------------------------------
# Level construction
# ---------------------------------------------------------------------------

def _build_level(rng: random.Random, depth: int, player_hp: int, player_max_hp: int,
                 player_attack: int, score: int) -> GameState:
    """Generate a fresh dungeon level and populate it with entities."""
    grid, rooms = D.generate(rng)

    # Collect floor tiles for entity placement.
    floor_tiles = D.all_floor_tiles(grid)

    # Player starts at the center of the first room.
    px, py = rooms[0].center
    occupied = {(px, py)}

    # Stairs go in the last room's center.
    sx, sy = rooms[-1].center
    grid = D.place_stairs(grid, sx, sy)
    occupied.add((sx, sy))

    # Pick placement spots, excluding already-occupied tiles.
    available = [t for t in floor_tiles if t not in occupied]

    n_monsters = MONSTERS_BASE + (depth - 1)
    n_items = ITEMS_BASE

    spots = _sample_distinct(available, n_monsters + n_items, rng)
    monster_spots = spots[:n_monsters]
    item_spots = spots[n_monsters:]

    glyphs = list(MONSTER_DEFS.keys())
    monsters_list = []
    for col, row in monster_spots:
        glyph = rng.choice(glyphs)
        base_hp, base_atk, _ = MONSTER_DEFS[glyph]
        hp = base_hp + (depth - 1)
        atk = base_atk + (depth - 1) // 2
        monsters_list.append(Monster(col=col, row=row, glyph=glyph, hp=hp, attack=atk))

    item_kinds = [POTION, GEAR]
    items_list = []
    for i, (col, row) in enumerate(item_spots):
        kind = item_kinds[i % len(item_kinds)]
        items_list.append(Item(col=col, row=row, kind=kind))

    player = Player(col=px, row=py, hp=player_hp, max_hp=player_max_hp,
                    attack=player_attack)

    return GameState(
        grid=grid,
        player=player,
        monsters=tuple(monsters_list),
        items=tuple(items_list),
        depth=depth,
        score=score,
        game_over=False,
    )


def new_game(rng: random.Random) -> GameState:
    """Start a brand-new game at depth 1."""
    return _build_level(rng, depth=1, player_hp=20, player_max_hp=20,
                        player_attack=3, score=0)


# ---------------------------------------------------------------------------
# Transitions
# ---------------------------------------------------------------------------

def _apply_items(state: GameState, col: int, row: int) -> GameState:
    """Pick up any item at (col, row) and return updated state."""
    item = _item_at(state.items, col, row)
    if item is None:
        return state

    remaining = tuple(it for it in state.items if it is not item)
    p = state.player

    if item.kind == POTION:
        new_hp = min(p.hp + HEAL_AMOUNT, p.max_hp)
        p = replace(p, hp=new_hp)
    elif item.kind == GEAR:
        p = replace(p, attack=p.attack + GEAR_ATTACK_BONUS)

    return replace(state, player=p, items=remaining)


def _monsters_act(state: GameState, rng: random.Random) -> GameState:
    """Every living monster takes one turn (move toward player or attack)."""
    p = state.player
    new_monsters = list(state.monsters)
    grid = state.grid

    for idx in range(len(new_monsters)):
        m = new_monsters[idx]
        if m.hp <= 0:
            continue

        dc = 0
        dr = 0
        # Greedy step: pick the axis that closes more distance first; break
        # ties by column to keep the AI deterministic without needing rng.
        col_dist = p.col - m.col
        row_dist = p.row - m.row

        if abs(col_dist) >= abs(row_dist):
            dc = 1 if col_dist > 0 else (-1 if col_dist < 0 else 0)
        else:
            dr = 1 if row_dist > 0 else (-1 if row_dist < 0 else 0)

        target_col = m.col + dc
        target_row = m.row + dr

        # Attack if stepping onto the player.
        if target_col == p.col and target_row == p.row:
            new_hp = p.hp - m.attack
            p = replace(p, hp=new_hp)
            new_monsters[idx] = m  # monster stays in place
            continue

        # Block if tile is a wall or occupied by another monster.
        other_occupied = {
            (new_monsters[j].col, new_monsters[j].row)
            for j in range(len(new_monsters))
            if j != idx and new_monsters[j].hp > 0
        }
        if (
            _is_walkable(grid, target_col, target_row)
            and (target_col, target_row) not in other_occupied
        ):
            new_monsters[idx] = replace(m, col=target_col, row=target_row)

    game_over = p.hp <= 0
    return replace(state, player=p, monsters=tuple(new_monsters), game_over=game_over)


def step(state: GameState, dcol: int, drow: int, rng: random.Random) -> GameState:
    """Attempt to move the player by (dcol, drow).

    Returns the *same* state object when the move is blocked by a wall so the
    caller can detect no-op moves via identity comparison.

    Turn sequence when the move succeeds:
      1. Bump-attack if a monster is at the destination.
      2. Otherwise move the player.
      3. Pick up any item at the new position.
      4. Every monster acts.
    """
    if state.game_over:
        return state

    p = state.player
    new_col = p.col + dcol
    new_row = p.row + drow

    # Wall check — return the same object so the loop skips monster turns.
    if not _is_walkable(state.grid, new_col, new_row):
        return state

    # Bump-to-attack: moving into a monster tile attacks it.
    target = _monster_at(state.monsters, new_col, new_row)
    if target is not None:
        new_hp = target.hp - p.attack
        if new_hp <= 0:
            # Monster dies — remove it and award score.
            survivors = tuple(m for m in state.monsters if m is not target)
            score_gain = 10 * state.depth
            state = replace(state, monsters=survivors, score=state.score + score_gain)
        else:
            updated = replace(target, hp=new_hp)
            new_monsters = tuple(m if m is not target else updated for m in state.monsters)
            state = replace(state, monsters=new_monsters)
        # Player didn't move; monsters still act.
        return _monsters_act(state, rng)

    # Move the player.
    p = replace(p, col=new_col, row=new_row)
    state = replace(state, player=p)

    # Pick up items.
    state = _apply_items(state, new_col, new_row)

    # Monsters act.
    state = _monsters_act(state, rng)
    return state


def descend(state: GameState, rng: random.Random) -> GameState:
    """Descend to the next level, keeping player stats and score."""
    p = state.player
    return _build_level(
        rng,
        depth=state.depth + 1,
        player_hp=p.hp,
        player_max_hp=p.max_hp,
        player_attack=p.attack,
        score=state.score,
    )


def restart(rng: random.Random) -> GameState:
    """Start a completely new game (called on 'r' when game_over)."""
    return new_game(rng)

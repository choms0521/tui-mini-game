"""Immutable game state and all transitions for Battleship.

Every transition takes a :class:`GameState` and returns a new one via
``dataclasses.replace``; nothing is mutated in place, so the game loop can
compare object identity to tell whether anything changed. Randomness (fleet
placement and the AI's choices) is injected via a ``random.Random`` instance so
the game logic is deterministic given the same seed.

Hit / miss / sunk are never stored: they are derived on demand from the shot
sets and the ships. The opponent AI (a classic hunt/target searcher) lives here,
not in main.py, so it stays pure and can be exercised by the selftest. The AI's
target-mode candidate queue is kept inside the state itself so its behaviour is
fully reproducible.
"""
from __future__ import annotations

import random
from dataclasses import dataclass, replace
from typing import FrozenSet, Optional, Tuple

import board as B

PLAYER = 0
AI = 1


@dataclass(frozen=True)
class Ship:
    """A single ship: its name, the cells it occupies, and its orientation."""

    name: str
    cells: FrozenSet[B.Pos]
    horizontal: bool


@dataclass(frozen=True)
class GameState:
    """Complete, immutable snapshot of one Battleship game.

    player_ships    -- the human's fleet (its own cells; hidden from the AI's view).
    ai_ships        -- the AI's fleet (cells hidden from the human's tracking board).
    player_shots    -- cells the human has fired at the AI fleet.
    ai_shots        -- cells the AI has fired at the human fleet.
    ai_target_queue -- AI target-mode candidate cells, kept in state for determinism.
    cursor          -- the human's aim position on the tracking board.
    current_turn    -- whose turn it is to fire (PLAYER or AI).
    game_over       -- True once one side has sunk the whole opposing fleet.
    winner          -- PLAYER, AI, or None while play continues.
    """

    player_ships: Tuple[Ship, ...]
    ai_ships: Tuple[Ship, ...]
    player_shots: FrozenSet[B.Pos]
    ai_shots: FrozenSet[B.Pos]
    ai_target_queue: Tuple[B.Pos, ...]
    cursor: B.Pos
    current_turn: int
    game_over: bool
    winner: Optional[int]


# ---------------------------------------------------------------------------
# Fleet placement
# ---------------------------------------------------------------------------

def _place_fleet(rng: random.Random, rows: int = B.ROWS,
                 cols: int = B.COLS) -> Tuple[Ship, ...]:
    """Randomly place the standard fleet with no overlaps (adjacency allowed).

    Ships are placed largest-first so the tight early board does not deadlock.
    Placement is deterministic for a given *rng*.
    """
    ships: list[Ship] = []
    occupied: set[B.Pos] = set()

    for name, length in B.FLEET:
        while True:
            horizontal = rng.random() < 0.5
            if horizontal:
                r = rng.randrange(rows)
                c = rng.randrange(cols - length + 1)
            else:
                r = rng.randrange(rows - length + 1)
                c = rng.randrange(cols)
            cells = B.ship_cells((r, c), length, horizontal)
            if any(cell in occupied for cell in cells):
                continue
            occupied.update(cells)
            ships.append(Ship(name=name, cells=frozenset(cells), horizontal=horizontal))
            break

    return tuple(ships)


def new_game(rng: random.Random) -> GameState:
    """Return a freshly started game with both fleets placed by *rng*.

    The human (PLAYER) fires first.
    """
    return GameState(
        player_ships=_place_fleet(rng),
        ai_ships=_place_fleet(rng),
        player_shots=frozenset(),
        ai_shots=frozenset(),
        ai_target_queue=(),
        cursor=(0, 0),
        current_turn=PLAYER,
        game_over=False,
        winner=None,
    )


# ---------------------------------------------------------------------------
# Derived queries (never stored)
# ---------------------------------------------------------------------------

def ship_at(ships: Tuple[Ship, ...], pos: B.Pos) -> Optional[Ship]:
    """Return the ship occupying *pos*, or None if the cell is open water."""
    for ship in ships:
        if pos in ship.cells:
            return ship
    return None


def is_hit(ships: Tuple[Ship, ...], pos: B.Pos) -> bool:
    """True when *pos* lands on any ship in *ships*."""
    return ship_at(ships, pos) is not None


def is_sunk(ship: Ship, shots: FrozenSet[B.Pos]) -> bool:
    """True when every cell of *ship* has been shot."""
    return ship.cells <= shots


def sunk_ships(ships: Tuple[Ship, ...], shots: FrozenSet[B.Pos]) -> Tuple[Ship, ...]:
    """Return the ships in *ships* that are fully sunk by *shots*."""
    return tuple(ship for ship in ships if is_sunk(ship, shots))


def ships_remaining(ships: Tuple[Ship, ...], shots: FrozenSet[B.Pos]) -> int:
    """Number of ships in *ships* not yet sunk by *shots*."""
    return sum(1 for ship in ships if not is_sunk(ship, shots))


def all_sunk(ships: Tuple[Ship, ...], shots: FrozenSet[B.Pos]) -> bool:
    """True when every ship in *ships* has been sunk by *shots*."""
    return all(is_sunk(ship, shots) for ship in ships)


def move_cursor(state: GameState, dr: int, dc: int) -> GameState:
    """Move the tracking-board cursor by (dr, dc), clamped to the grid bounds."""
    if state.game_over:
        return state
    r, c = state.cursor
    new_r = max(0, min(B.ROWS - 1, r + dr))
    new_c = max(0, min(B.COLS - 1, c + dc))
    if (new_r, new_c) == state.cursor:
        return state
    return replace(state, cursor=(new_r, new_c))


# ---------------------------------------------------------------------------
# Shot resolution
# ---------------------------------------------------------------------------

def player_fire(state: GameState, pos: Optional[B.Pos] = None) -> GameState:
    """Fire the human's shot at *pos* (defaults to the cursor) on the AI fleet.

    Returns the same state object when the move is illegal (game over, not the
    human's turn, or the cell was already shot), so the caller can tell nothing
    changed. A hit lets the human keep firing is *not* a rule here: each shot
    passes the turn to the AI (handled by the caller).
    """
    if state.game_over or state.current_turn != PLAYER:
        return state
    target = state.cursor if pos is None else pos
    if target in state.player_shots:
        return state

    new_shots = state.player_shots | {target}
    if all_sunk(state.ai_ships, new_shots):
        return replace(state, player_shots=new_shots, game_over=True, winner=PLAYER)
    return replace(state, player_shots=new_shots, current_turn=AI)


# ---------------------------------------------------------------------------
# Opponent AI: hunt / target searcher
# ---------------------------------------------------------------------------

def _unshot_cells(shots: FrozenSet[B.Pos]) -> list[B.Pos]:
    """Return every board cell that has not been fired at yet."""
    return [(r, c) for r in range(B.ROWS) for c in range(B.COLS) if (r, c) not in shots]


def _hunt_target(rng: random.Random, shots: FrozenSet[B.Pos]) -> B.Pos:
    """Pick an un-shot cell, preferring the checkerboard parity for efficiency.

    The two smallest ships are length 2, so a single parity class still covers
    every possible ship. When the parity class is exhausted we fall back to any
    remaining cell so the AI never returns an already-shot square.
    """
    cells = _unshot_cells(shots)
    parity = [pos for pos in cells if (pos[0] + pos[1]) % 2 == 0]
    pool = parity if parity else cells
    return rng.choice(pool)


def _enqueue_neighbours(
    queue: Tuple[B.Pos, ...],
    hit: B.Pos,
    shots: FrozenSet[B.Pos],
    hits_on_target: FrozenSet[B.Pos],
) -> Tuple[B.Pos, ...]:
    """Return *queue* extended with the un-shot orthogonal neighbours of *hit*.

    Once two hits line up (share a row or column), neighbours along that line are
    prioritised: the candidates continuing the line are placed at the front so
    the AI keeps firing along a discovered ship instead of poking sideways.
    """
    fresh = [
        pos for pos in B.neighbours(hit)
        if pos not in shots and pos not in queue
    ]

    aligned = [h for h in hits_on_target if h != hit and (h[0] == hit[0] or h[1] == hit[1])]
    if aligned:
        partner = aligned[0]
        if partner[0] == hit[0]:  # same row -> ship runs horizontally
            on_line = [pos for pos in fresh if pos[0] == hit[0]]
            off_line = [pos for pos in fresh if pos[0] != hit[0]]
        else:                      # same column -> ship runs vertically
            on_line = [pos for pos in fresh if pos[1] == hit[1]]
            off_line = [pos for pos in fresh if pos[1] != hit[1]]
        # On-line candidates first (front of queue), then the rest.
        return tuple(on_line) + queue + tuple(off_line)

    return queue + tuple(fresh)


def _prune_sunk(
    queue: Tuple[B.Pos, ...],
    player_ships: Tuple[Ship, ...],
    shots: FrozenSet[B.Pos],
) -> Tuple[B.Pos, ...]:
    """Drop target candidates orphaned when a ship is confirmed sunk.

    A candidate is only worth keeping while it still borders a hit on a ship that
    has not yet sunk. After a sink, the neighbours that merely surrounded the
    destroyed ship no longer touch a live hit and are dropped, so the AI stops
    chasing dead candidates; the candidates of a still-floating adjacent ship are
    kept so a known hit is never abandoned. When no un-sunk hits remain the queue
    empties and the AI falls back to hunt mode.
    """
    live_hits = frozenset(
        pos
        for ship in player_ships
        if not is_sunk(ship, shots)
        for pos in ship.cells
        if pos in shots
    )
    return tuple(
        pos for pos in queue
        if any(neighbour in live_hits for neighbour in B.neighbours(pos))
    )


def _next_ai_shot(state: GameState, rng: random.Random) -> Tuple[B.Pos, Tuple[B.Pos, ...]]:
    """Return the AI's next legal (un-shot) cell and the queue to fire it from.

    Target mode drains the queue (skipping any already-shot entries) before
    falling back to hunt mode. The returned queue still contains the chosen cell;
    it is consumed in :func:`ai_fire` after the shot resolves.
    """
    queue = tuple(pos for pos in state.ai_target_queue if pos not in state.ai_shots)
    if queue:
        return queue[0], queue
    return _hunt_target(rng, state.ai_shots), ()


def ai_fire(state: GameState, rng: random.Random) -> GameState:
    """Fire the AI's next shot at the human fleet and return the new state.

    Uses the hunt/target strategy: in hunt mode it picks a parity cell at random;
    after a hit it enqueues the hit's orthogonal neighbours (preferring the line
    once two hits align) and works the queue until the ship sinks, at which point
    candidates that no longer border a live hit are pruned and the AI falls back
    to hunt mode once no un-sunk hits remain.
    Returns the same state object when it is not the AI's turn or the game is over.
    """
    if state.game_over or state.current_turn != AI:
        return state

    target, queue = _next_ai_shot(state, rng)
    new_shots = state.ai_shots | {target}
    # Remove the cell we just fired from the working queue.
    new_queue = tuple(pos for pos in queue if pos != target)

    hit = is_hit(state.player_ships, target)
    if hit:
        ship = ship_at(state.player_ships, target)
        assert ship is not None  # guaranteed by the is_hit check
        if is_sunk(ship, new_shots):
            # Ship destroyed: drop its dead leftovers, keep any live adjacent hit.
            new_queue = _prune_sunk(new_queue, state.player_ships, new_shots)
        else:
            hits_on_player = frozenset(
                pos for pos in new_shots if is_hit(state.player_ships, pos)
            )
            new_queue = _enqueue_neighbours(new_queue, target, new_shots, hits_on_player)

    if all_sunk(state.player_ships, new_shots):
        return replace(
            state,
            ai_shots=new_shots,
            ai_target_queue=new_queue,
            game_over=True,
            winner=AI,
        )

    return replace(
        state,
        ai_shots=new_shots,
        ai_target_queue=new_queue,
        current_turn=PLAYER,
    )

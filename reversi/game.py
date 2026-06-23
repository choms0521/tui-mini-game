"""Immutable game state and the transitions that drive a game of Reversi.

Every transition takes a :class:`GameState` and returns a new one via
``dataclasses.replace``, so the game loop can compare object identity to tell
whether anything actually changed. The board is a tuple-of-tuples so a state is
a fully immutable value. Legal moves and the discs a move flips are derived by
pure functions and never stored on the state.

The opponent AI is a depth-limited minimax with alpha-beta pruning. It lives
here (not in main.py) so it stays pure and can be exercised by the selftest.

A key Reversi wrinkle is that turns do not strictly alternate: a player who has
no legal move is skipped (a "pass"). After every placement the next player is
chosen by :func:`_next_player`, so ``current_player`` always points at someone
who actually has a move, and a pass needs no separate code path or key press.
"""
from __future__ import annotations

import random
from dataclasses import dataclass, replace
from typing import List, Optional, Tuple

import board as B

BLACK = B.BLACK      # disc colors, re-exported for callers and tests
WHITE = B.WHITE
HUMAN = B.BLACK      # the human plays black and moves first
AI = B.WHITE         # the AI plays white
AI_DEPTH = 4         # default minimax search depth

Board = Tuple[Tuple[int, ...], ...]

_WIN_SCORE = 10_000_000

# Positional weight matrix from the side-to-move's perspective. Corners are very
# valuable, the X/C squares next to a corner are dangerous (they hand the corner
# to the opponent), edges are mildly good. Used by the static evaluation.
_WEIGHTS: Tuple[Tuple[int, ...], ...] = (
    (120, -20, 20,  5,  5, 20, -20, 120),
    (-20, -40, -5, -5, -5, -5, -40, -20),
    (20,   -5, 15,  3,  3, 15,  -5,  20),
    (5,    -5,  3,  3,  3,  3,  -5,   5),
    (5,    -5,  3,  3,  3,  3,  -5,   5),
    (20,   -5, 15,  3,  3, 15,  -5,  20),
    (-20, -40, -5, -5, -5, -5, -40, -20),
    (120, -20, 20,  5,  5, 20, -20, 120),
)


@dataclass(frozen=True)
class GameState:
    """Complete, immutable state of one Reversi game.

    board          -- SIZE x SIZE grid; 0 empty, 1 black (human), 2 white (AI).
    current_player -- whose turn it is (HUMAN or AI); always someone with a move
                      until the game is over.
    game_over      -- True once neither player can move (or the board is full).
    winner         -- HUMAN, AI, 0 for a draw, or None while play continues.
    last_move      -- the most recently placed position, or None at the start.
    cursor         -- the cell the human's cursor is currently over.
    """

    board: Board
    current_player: int
    game_over: bool
    winner: Optional[int]
    last_move: Optional[B.Pos]
    cursor: B.Pos


def _other(player: int) -> int:
    """Return the opposing player."""
    return HUMAN if player == AI else AI


def new_game() -> GameState:
    """Create a fresh game with the standard four-disc centre setup.

    White sits on (3,3) and (4,4); black sits on (3,4) and (4,3). Black (the
    human) moves first.
    """
    start = {
        (3, 3): B.WHITE, (4, 4): B.WHITE,
        (3, 4): B.BLACK, (4, 3): B.BLACK,
    }
    board = tuple(
        tuple(start.get((r, c), B.EMPTY) for c in range(B.SIZE))
        for r in range(B.SIZE)
    )
    return GameState(
        board=board,
        current_player=HUMAN,
        game_over=False,
        winner=None,
        last_move=None,
        cursor=(3, 3),
    )


# ---------------------------------------------------------------------------
# Pure move logic: outflanking, legal moves, and applying a placement
# ---------------------------------------------------------------------------

def _flips_in_direction(
    board: Board, pos: B.Pos, player: int, direction: B.Pos
) -> List[B.Pos]:
    """Return the discs *player* would flip from *pos* along *direction*.

    A direction qualifies only when it crosses one or more contiguous opponent
    discs and then lands on one of *player*'s own discs. Otherwise the captured
    line is empty (running off the edge or hitting a blank breaks the chain).
    """
    opp = _other(player)
    dr, dc = direction
    r, c = pos[0] + dr, pos[1] + dc
    captured: List[B.Pos] = []
    while B.in_bounds(r, c) and board[r][c] == opp:
        captured.append((r, c))
        r += dr
        c += dc
    if captured and B.in_bounds(r, c) and board[r][c] == player:
        return captured
    return []


def flips_for_move(board: Board, pos: B.Pos, player: int) -> List[B.Pos]:
    """Return every disc *player* would flip by placing at *pos*.

    Returns an empty list when *pos* is occupied or outflanks nothing, i.e. the
    move is illegal exactly when this list is empty.
    """
    row, col = pos
    if board[row][col] != B.EMPTY:
        return []
    captured: List[B.Pos] = []
    for direction in B.DIRECTIONS:
        captured.extend(_flips_in_direction(board, pos, player, direction))
    return captured


def legal_moves(board: Board, player: int) -> List[B.Pos]:
    """Return every position where *player* can legally place a disc."""
    moves: List[B.Pos] = []
    for r in range(B.SIZE):
        for c in range(B.SIZE):
            if board[r][c] == B.EMPTY and flips_for_move(board, (r, c), player):
                moves.append((r, c))
    return moves


def _apply(board: Board, pos: B.Pos, player: int, flipped: List[B.Pos]) -> Board:
    """Return a new board with *player* placed at *pos* and *flipped* recolored."""
    changed = {pos: player}
    for fp in flipped:
        changed[fp] = player
    return tuple(
        tuple(changed.get((r, c), board[r][c]) for c in range(B.SIZE))
        for r in range(B.SIZE)
    )


def disc_counts(board: Board) -> Tuple[int, int]:
    """Return (black_count, white_count) on *board*."""
    black = sum(row.count(B.BLACK) for row in board)
    white = sum(row.count(B.WHITE) for row in board)
    return black, white


def _winner_by_count(board: Board) -> int:
    """Return the winner purely by disc count (0 means a draw)."""
    black, white = disc_counts(board)
    if black > white:
        return B.BLACK
    if white > black:
        return B.WHITE
    return 0


def _next_player(board: Board, mover: int) -> Tuple[int, bool, Optional[int]]:
    """Decide who moves next after *mover* has just placed on *board*.

    Returns (next_player, game_over, winner). The opponent moves next if it has
    a legal move; otherwise *mover* keeps the turn if it still has one (the
    opponent has passed); if neither can move the game is over.
    """
    opponent = _other(mover)
    if legal_moves(board, opponent):
        return opponent, False, None
    if legal_moves(board, mover):
        return mover, False, None
    return mover, True, _winner_by_count(board)


def place(state: GameState, pos: B.Pos) -> GameState:
    """Place the current player's disc at *pos*.

    Returns the same state object when the move is illegal (game over or *pos*
    does not outflank anything), so the caller can tell nothing changed.
    """
    if state.game_over:
        return state
    flipped = flips_for_move(state.board, pos, state.current_player)
    if not flipped:
        return state

    new_board = _apply(state.board, pos, state.current_player, flipped)
    next_player, game_over, winner = _next_player(new_board, state.current_player)
    return replace(
        state,
        board=new_board,
        current_player=next_player,
        game_over=game_over,
        winner=winner,
        last_move=pos,
    )


# ---------------------------------------------------------------------------
# Opponent AI: depth-limited minimax with alpha-beta pruning
# ---------------------------------------------------------------------------

def _evaluate(board: Board, player: int) -> int:
    """Static evaluation of *board* from *player*'s perspective.

    Combines positional weights, the raw disc difference, and a mobility
    difference (how many more moves the player has than the opponent). The
    weight matrix dominates so corners and edges drive the AI's strategy.
    """
    opp = _other(player)

    positional = 0
    for r in range(B.SIZE):
        for c in range(B.SIZE):
            cell = board[r][c]
            if cell == player:
                positional += _WEIGHTS[r][c]
            elif cell == opp:
                positional -= _WEIGHTS[r][c]

    black, white = disc_counts(board)
    own, other = (black, white) if player == B.BLACK else (white, black)
    disc_diff = own - other

    my_moves = len(legal_moves(board, player))
    opp_moves = len(legal_moves(board, opp))
    mobility = my_moves - opp_moves

    return positional + disc_diff + 5 * mobility


def _minimax(
    board: Board,
    to_move: int,
    depth: int,
    alpha: int,
    beta: int,
    player: int,
) -> int:
    """Return the minimax value of *board* for *player* (the AI being optimized).

    *to_move* is whichever side acts at this node; it may differ from *player*.
    A side with no legal move passes (recurse with the same board for the
    opponent); if neither side can move the node is terminal and scored by the
    final disc difference. ``depth`` nudges the AI toward sooner wins.
    """
    opp = _other(to_move)
    my_moves = legal_moves(board, to_move)

    if not my_moves:
        if not legal_moves(board, opp):
            # Neither side can move: terminal node, decide by disc difference.
            winner = _winner_by_count(board)
            if winner == player:
                return _WIN_SCORE + depth
            if winner == _other(player):
                return -_WIN_SCORE - depth
            return 0
        # Current side passes; the opponent acts without consuming depth's move.
        return _minimax(board, opp, depth, alpha, beta, player)

    if depth == 0:
        return _evaluate(board, player)

    maximizing = to_move == player
    if maximizing:
        value = -_WIN_SCORE * 2
        for pos in my_moves:
            child = _apply(board, pos, to_move, flips_for_move(board, pos, to_move))
            value = max(value, _minimax(child, opp, depth - 1, alpha, beta, player))
            alpha = max(alpha, value)
            if alpha >= beta:
                break
        return value

    value = _WIN_SCORE * 2
    for pos in my_moves:
        child = _apply(board, pos, to_move, flips_for_move(board, pos, to_move))
        value = min(value, _minimax(child, opp, depth - 1, alpha, beta, player))
        beta = min(beta, value)
        if alpha >= beta:
            break
    return value


def ai_move(
    state: GameState, rng: random.Random, depth: int = AI_DEPTH
) -> Optional[B.Pos]:
    """Return the position the AI should play, or None if it has no legal move.

    Ties between equally-good positions are broken with *rng* so the AI is not
    perfectly predictable; passing a seeded Random keeps the choice deterministic
    for the selftest.
    """
    player = state.current_player
    opp = _other(player)
    moves = legal_moves(state.board, player)
    if not moves:
        return None

    best_value = -_WIN_SCORE * 3
    best_moves: List[B.Pos] = []
    for pos in moves:
        child = _apply(state.board, pos, player, flips_for_move(state.board, pos, player))
        value = _minimax(child, opp, depth - 1, -_WIN_SCORE * 2, _WIN_SCORE * 2, player)
        if value > best_value:
            best_value = value
            best_moves = [pos]
        elif value == best_value:
            best_moves.append(pos)

    return rng.choice(best_moves)

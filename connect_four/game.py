"""Immutable game state and the transitions that drive a game of Connect Four.

Every transition takes a :class:`GameState` and returns a new one via
``dataclasses.replace``, so the game loop can compare object identity to tell
whether anything actually changed. The board is a tuple-of-tuples so a state is
a fully immutable value.

The opponent AI is a depth-limited minimax with alpha-beta pruning. It lives
here (not in main.py) so it stays pure and can be exercised by the selftest.
"""
from __future__ import annotations

import random
from dataclasses import dataclass, replace
from typing import List, Optional, Tuple

import board as B

HUMAN = 1
AI = 2
CONNECT = 4          # how many in a row wins
AI_DEPTH = 4         # default minimax search depth

Board = Tuple[Tuple[int, ...], ...]

_WIN_SCORE = 10_000_000


@dataclass(frozen=True)
class GameState:
    """Complete, immutable state of one Connect Four game.

    board          -- ROWS x COLS grid; 0 empty, 1 human, 2 AI. Row 0 is the top.
    current_player -- whose turn it is (HUMAN or AI).
    game_over      -- True once someone has won or the board is full.
    winner         -- HUMAN, AI, 0 for a draw, or None while play continues.
    last_move      -- column of the most recent drop, or None at the start.
    """

    board: Board
    current_player: int
    game_over: bool
    winner: Optional[int]
    last_move: Optional[int]


def new_game() -> GameState:
    """Create a fresh game with an empty board; the human moves first."""
    board = tuple(tuple(B.EMPTY for _ in range(B.COLS)) for _ in range(B.ROWS))
    return GameState(
        board=board,
        current_player=HUMAN,
        game_over=False,
        winner=None,
        last_move=None,
    )


def _other(player: int) -> int:
    """Return the opposing player."""
    return HUMAN if player == AI else AI


def valid_moves(board: Board) -> List[int]:
    """Return the columns that still have room for a disc."""
    return [c for c in range(B.COLS) if board[0][c] == B.EMPTY]


def _landing_row(board: Board, col: int) -> Optional[int]:
    """Return the row a disc dropped in *col* would land in, or None if full."""
    for r in range(B.ROWS - 1, -1, -1):
        if board[r][col] == B.EMPTY:
            return r
    return None


def _place(board: Board, row: int, col: int, player: int) -> Board:
    """Return a new board with *player* placed at (row, col)."""
    return tuple(
        tuple(
            player if (r == row and c == col) else board[r][c]
            for c in range(B.COLS)
        )
        for r in range(B.ROWS)
    )


def _wins_at(board: Board, row: int, col: int) -> bool:
    """True when the disc at (row, col) completes a line of CONNECT."""
    player = board[row][col]
    if player == B.EMPTY:
        return False
    for dr, dc in B.DIRECTIONS:
        count = 1
        r, c = row + dr, col + dc
        while B.in_bounds(r, c) and board[r][c] == player:
            count += 1
            r += dr
            c += dc
        r, c = row - dr, col - dc
        while B.in_bounds(r, c) and board[r][c] == player:
            count += 1
            r -= dr
            c -= dc
        if count >= CONNECT:
            return True
    return False


def check_winner(board: Board) -> Optional[int]:
    """Scan the whole board and return the winning player, or None."""
    for r in range(B.ROWS):
        for c in range(B.COLS):
            if board[r][c] != B.EMPTY and _wins_at(board, r, c):
                return board[r][c]
    return None


def drop(state: GameState, col: int) -> GameState:
    """Drop the current player's disc into *col*.

    Returns the same state object when the move is illegal (game over or the
    column is full or out of range), so the caller can tell nothing changed.
    """
    if state.game_over or col not in valid_moves(state.board):
        return state

    row = _landing_row(state.board, col)
    assert row is not None  # guaranteed by the valid_moves check above
    new_board = _place(state.board, row, col, state.current_player)

    if _wins_at(new_board, row, col):
        return replace(
            state,
            board=new_board,
            game_over=True,
            winner=state.current_player,
            last_move=col,
        )
    if not valid_moves(new_board):
        return replace(
            state, board=new_board, game_over=True, winner=0, last_move=col
        )
    return replace(
        state,
        board=new_board,
        current_player=_other(state.current_player),
        last_move=col,
    )


# ---------------------------------------------------------------------------
# Opponent AI: depth-limited minimax with alpha-beta pruning
# ---------------------------------------------------------------------------

def _score_window(window: Tuple[int, ...], player: int) -> int:
    """Heuristic score for one 4-cell window from *player*'s perspective."""
    opp = _other(player)
    own = window.count(player)
    other = window.count(opp)
    empty = window.count(B.EMPTY)

    if own == 4:
        return 100
    if own == 3 and empty == 1:
        return 5
    if own == 2 and empty == 2:
        return 2
    if other == 3 and empty == 1:
        return -4  # an open opponent threat is dangerous
    return 0


def _evaluate(board: Board, player: int) -> int:
    """Static evaluation of *board* from *player*'s perspective."""
    score = 0
    # Prefer the center column: it participates in the most lines.
    center = B.COLS // 2
    score += sum(1 for r in range(B.ROWS) if board[r][center] == player) * 3

    for r in range(B.ROWS):
        for c in range(B.COLS):
            for dr, dc in B.DIRECTIONS:
                end_r, end_c = r + dr * (CONNECT - 1), c + dc * (CONNECT - 1)
                if not B.in_bounds(end_r, end_c):
                    continue
                window = tuple(board[r + dr * k][c + dc * k] for k in range(CONNECT))
                score += _score_window(window, player)
    return score


def _minimax(
    board: Board,
    depth: int,
    alpha: int,
    beta: int,
    maximizing: bool,
    player: int,
) -> int:
    """Return the minimax value of *board* for *player* (the AI being optimized).

    A win for *player* deep in the tree is worth slightly less than a shallow one
    (``depth`` is added/subtracted) so the AI prefers to win sooner and stall
    losing longer.
    """
    winner = check_winner(board)
    if winner == player:
        return _WIN_SCORE + depth
    if winner == _other(player):
        return -_WIN_SCORE - depth
    moves = valid_moves(board)
    if not moves:
        return 0  # draw
    if depth == 0:
        return _evaluate(board, player)

    if maximizing:
        value = -_WIN_SCORE * 2
        for col in moves:
            row = _landing_row(board, col)
            child = _place(board, row, col, player)
            value = max(value, _minimax(child, depth - 1, alpha, beta, False, player))
            alpha = max(alpha, value)
            if alpha >= beta:
                break
        return value

    opp = _other(player)
    value = _WIN_SCORE * 2
    for col in moves:
        row = _landing_row(board, col)
        child = _place(board, row, col, opp)
        value = min(value, _minimax(child, depth - 1, alpha, beta, True, player))
        beta = min(beta, value)
        if alpha >= beta:
            break
    return value


def ai_move(state: GameState, rng: random.Random, depth: int = AI_DEPTH) -> Optional[int]:
    """Return the column the AI should play, or None if the board is full.

    Ties between equally-good columns are broken with *rng* so the AI is not
    perfectly predictable; passing a seeded Random keeps the choice deterministic
    for the selftest.
    """
    player = state.current_player
    moves = valid_moves(state.board)
    if not moves:
        return None

    best_value = -_WIN_SCORE * 3
    best_cols: List[int] = []
    for col in moves:
        row = _landing_row(state.board, col)
        child = _place(state.board, row, col, player)
        # If this move wins outright, score it directly (avoids a needless ply).
        if _wins_at(child, row, col):
            value = _WIN_SCORE + depth
        else:
            value = _minimax(child, depth - 1, -_WIN_SCORE * 2, _WIN_SCORE * 2, False, player)
        if value > best_value:
            best_value = value
            best_cols = [col]
        elif value == best_value:
            best_cols.append(col)

    return rng.choice(best_cols)

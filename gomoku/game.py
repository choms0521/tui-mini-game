"""Immutable game state and the transitions that drive a game of Gomoku.

Every transition takes a :class:`GameState` and returns a new one via
``dataclasses.replace``, so the game loop can compare object identity to tell
whether anything actually changed. The board is a tuple-of-tuples so a state is
a fully immutable value.

The opponent AI is a threat-pattern heuristic. It lives here (not in main.py)
so it stays pure and can be exercised by the selftest. It never depends on
blessed.
"""
from __future__ import annotations

import random
from dataclasses import dataclass, replace
from typing import List, Optional, Tuple

import board as B

HUMAN = 1   # black stone, moves first
AI = 2      # white stone

# Radius around existing stones within which the AI considers empty cells.
# Both the immediate winning cell and the immediate blocking cell are within
# radius 1 of an existing stone, so radius 2 always includes them.
AI_RADIUS = 2

Board = Tuple[Tuple[int, ...], ...]
Pos = B.Pos

# Pattern scores used by the AI's static cell evaluation. A "5" (win) dominates
# everything; an open four (would win next ply unless blocked) is the next most
# urgent, and so on. Defensive scores reuse the same scale so one cell can be
# judged for offence and defence at once.
_SCORE_FIVE = 1_000_000
_SCORE_OPEN_FOUR = 100_000
_SCORE_FOUR = 10_000
_SCORE_OPEN_THREE = 5_000
_SCORE_THREE = 500
_SCORE_OPEN_TWO = 100
_SCORE_TWO = 10


@dataclass(frozen=True)
class GameState:
    """Complete, immutable state of one Gomoku game.

    board          -- ROWS x COLS grid; 0 empty, 1 human (black), 2 AI (white).
    current_player -- whose turn it is (HUMAN or AI).
    game_over      -- True once someone has won or the board is full.
    winner         -- HUMAN, AI, 0 for a draw, or None while play continues.
    last_move      -- position of the most recent stone, or None at the start.
    cursor         -- the cell the human is aiming at.
    """

    board: Board
    current_player: int
    game_over: bool
    winner: Optional[int]
    last_move: Optional[Pos]
    cursor: Pos


def new_game() -> GameState:
    """Create a fresh game with an empty board; the human (black) moves first."""
    board = tuple(tuple(B.EMPTY for _ in range(B.COLS)) for _ in range(B.ROWS))
    return GameState(
        board=board,
        current_player=HUMAN,
        game_over=False,
        winner=None,
        last_move=None,
        cursor=(B.ROWS // 2, B.COLS // 2),
    )


def _other(player: int) -> int:
    """Return the opposing player."""
    return HUMAN if player == AI else AI


def empty_cells(board: Board) -> List[Pos]:
    """Return every empty intersection on the board, in (row, col) order."""
    return [
        (r, c)
        for r in range(B.ROWS)
        for c in range(B.COLS)
        if board[r][c] == B.EMPTY
    ]


def _place(board: Board, row: int, col: int, player: int) -> Board:
    """Return a new board with *player* placed at (row, col)."""
    return tuple(
        tuple(
            player if (r == row and c == col) else board[r][c]
            for c in range(B.COLS)
        )
        for r in range(B.ROWS)
    )


def _run_length(board: Board, row: int, col: int, dr: int, dc: int) -> int:
    """Length of the contiguous run of board[row][col]'s colour through (dr, dc).

    Counts the stone at (row, col) itself plus equal-coloured stones in both the
    (dr, dc) and the opposite direction.
    """
    player = board[row][col]
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
    return count


def _wins_at(board: Board, row: int, col: int) -> bool:
    """True when the stone at (row, col) completes a run of WIN_LENGTH or more."""
    if board[row][col] == B.EMPTY:
        return False
    for dr, dc in B.DIRECTIONS:
        if _run_length(board, row, col, dr, dc) >= B.WIN_LENGTH:
            return True
    return False


def check_winner(board: Board) -> Optional[int]:
    """Scan the whole board and return the winning player, or None."""
    for r in range(B.ROWS):
        for c in range(B.COLS):
            if board[r][c] != B.EMPTY and _wins_at(board, r, c):
                return board[r][c]
    return None


def move_cursor(state: GameState, drow: int, dcol: int) -> GameState:
    """Move the aiming cursor by (drow, dcol), clamped to the board.

    Returns the same state object when the cursor would not move, so the caller
    can compare identity to decide whether to redraw.
    """
    r, c = state.cursor
    nr = min(max(r + drow, 0), B.ROWS - 1)
    nc = min(max(c + dcol, 0), B.COLS - 1)
    if (nr, nc) == state.cursor:
        return state
    return replace(state, cursor=(nr, nc))


def set_cursor(state: GameState, pos: Pos) -> GameState:
    """Return *state* with the aiming cursor at *pos*, clamped to the board.

    Used by the game loop to restore the human's aim after the AI replies, since
    :func:`place_at` moves the cursor to the stone it places.
    """
    r, c = pos
    nr = min(max(r, 0), B.ROWS - 1)
    nc = min(max(c, 0), B.COLS - 1)
    if (nr, nc) == state.cursor:
        return state
    return replace(state, cursor=(nr, nc))


def place(state: GameState) -> GameState:
    """Place the current player's stone at the cursor.

    Returns the same state object when the move is illegal (game over or the
    cell is already occupied), so the caller can tell nothing changed.
    """
    return place_at(state, state.cursor)


def place_at(state: GameState, pos: Pos) -> GameState:
    """Place the current player's stone at *pos* (also moving the cursor there).

    Used both by :func:`place` (human, cursor already at *pos*) and by the game
    loop to apply the AI's chosen move. Returns the same state object when the
    move is illegal (game over or the cell is already occupied).
    """
    if state.game_over:
        return state
    row, col = pos
    if not B.in_bounds(row, col):
        return state
    if state.board[row][col] != B.EMPTY:
        return state
    state = replace(state, cursor=pos)

    new_board = _place(state.board, row, col, state.current_player)

    if _wins_at(new_board, row, col):
        return replace(
            state,
            board=new_board,
            game_over=True,
            winner=state.current_player,
            last_move=(row, col),
        )
    if not empty_cells(new_board):
        return replace(
            state,
            board=new_board,
            game_over=True,
            winner=0,
            last_move=(row, col),
        )
    return replace(
        state,
        board=new_board,
        current_player=_other(state.current_player),
        last_move=(row, col),
    )


# ---------------------------------------------------------------------------
# Opponent AI: threat-pattern heuristic over a bounded candidate set
# ---------------------------------------------------------------------------

def _candidates(board: Board) -> List[Pos]:
    """Empty cells within AI_RADIUS of an existing stone, in (row, col) order.

    On an empty board the only candidate is the centre. Keeping the result in a
    deterministic sorted order is important so the seeded RNG tie-break stays
    reproducible.
    """
    occupied = [
        (r, c)
        for r in range(B.ROWS)
        for c in range(B.COLS)
        if board[r][c] != B.EMPTY
    ]
    if not occupied:
        return [(B.ROWS // 2, B.COLS // 2)]

    seen = set()
    for r, c in occupied:
        for dr in range(-AI_RADIUS, AI_RADIUS + 1):
            for dc in range(-AI_RADIUS, AI_RADIUS + 1):
                nr, nc = r + dr, c + dc
                if B.in_bounds(nr, nc) and board[nr][nc] == B.EMPTY:
                    seen.add((nr, nc))
    return sorted(seen)


def _line_score(board: Board, row: int, col: int, player: int) -> int:
    """Heuristic value of placing *player* at the empty cell (row, col).

    Scores the four orientations through the cell using the run length the move
    would create and whether the run's ends are open, then sums them. The cell
    is assumed empty; the stone is considered placed for the duration of the
    scan without mutating the board.
    """
    total = 0
    for dr, dc in B.DIRECTIONS:
        run = 1  # the stone we are placing at (row, col)

        # Forward arm.
        r, c = row + dr, col + dc
        while B.in_bounds(r, c) and board[r][c] == player:
            run += 1
            r += dr
            c += dc
        forward_open = B.in_bounds(r, c) and board[r][c] == B.EMPTY

        # Backward arm.
        r, c = row - dr, col - dc
        while B.in_bounds(r, c) and board[r][c] == player:
            run += 1
            r -= dr
            c -= dc
        backward_open = B.in_bounds(r, c) and board[r][c] == B.EMPTY

        open_ends = int(forward_open) + int(backward_open)
        total += _run_value(run, open_ends)
    return total


def _run_value(run: int, open_ends: int) -> int:
    """Map a (run length, open ends) pair to a threat score."""
    if run >= B.WIN_LENGTH:
        return _SCORE_FIVE
    if open_ends == 0:
        return 0  # a fully blocked short run is worthless
    if run == 4:
        return _SCORE_OPEN_FOUR if open_ends == 2 else _SCORE_FOUR
    if run == 3:
        return _SCORE_OPEN_THREE if open_ends == 2 else _SCORE_THREE
    if run == 2:
        return _SCORE_OPEN_TWO if open_ends == 2 else _SCORE_TWO
    return 1


def ai_move(state: GameState, rng: random.Random) -> Optional[Pos]:
    """Return the empty cell the AI should play, or None if the board is full.

    Priority, evaluated over a bounded candidate set:
      1. play a cell that immediately makes five (own win);
      2. block a cell where the opponent would immediately make five;
      3. otherwise pick the cell with the highest combined offence/defence score.

    Ties are broken with *rng* over a deterministically ordered candidate list,
    so passing a seeded Random keeps the choice reproducible for the selftest.
    """
    player = state.current_player
    opp = _other(player)
    candidates = _candidates(state.board)
    if not candidates:
        return None

    # 1. Immediate win for the AI.
    own_wins = [
        pos for pos in candidates
        if _wins_at(_place(state.board, pos[0], pos[1], player), pos[0], pos[1])
    ]
    if own_wins:
        return rng.choice(own_wins)

    # 2. Block the opponent's immediate win (covers an open four, which is just a
    #    cell where the opponent would make five).
    opp_wins = [
        pos for pos in candidates
        if _wins_at(_place(state.board, pos[0], pos[1], opp), pos[0], pos[1])
    ]
    if opp_wins:
        return rng.choice(opp_wins)

    # 3. Combined offence + defence pattern score.
    best_value = -1
    best_cells: List[Pos] = []
    for row, col in candidates:
        offence = _line_score(state.board, row, col, player)
        defence = _line_score(state.board, row, col, opp)
        value = offence + defence
        if value > best_value:
            best_value = value
            best_cells = [(row, col)]
        elif value == best_value:
            best_cells.append((row, col))

    return rng.choice(best_cells)

"""Immutable game state and the transitions that drive a game of Mastermind.

Every transition takes a :class:`GameState` and returns a new one via
``dataclasses.replace``, so the game loop can compare object identity to tell
whether anything actually changed. Randomness lives outside the state:
``new_game`` receives a ``random.Random`` so the state itself stays a pure value
and the selftest is fully deterministic.
"""
from __future__ import annotations

import random
from collections import Counter
from dataclasses import dataclass, replace
from typing import Tuple

CODE_LENGTH = 4    # number of pegs in the secret code
NUM_COLORS = 6     # colors are encoded as integers 1..NUM_COLORS
MAX_GUESSES = 10   # how many guesses the player gets before losing

Code = Tuple[int, ...]
# Feedback for one guess: (exact, partial).
# exact   -- pegs with the correct color AND the correct position.
# partial -- pegs with a correct color in the wrong position.
Feedback = Tuple[int, int]


@dataclass(frozen=True)
class GameState:
    """Complete, immutable state of one Mastermind round.

    secret      -- the hidden code the player is trying to break.
    guesses     -- submitted guesses, oldest first, up to ``max_guesses``.
    feedbacks   -- (exact, partial) per submitted guess, parallel to ``guesses``.
    current     -- pegs the player has entered for the next guess, left to right.
    max_guesses -- how many guesses are allowed before the game is lost.
    game_over   -- True once the player has won or run out of guesses.
    won         -- True only when a guess matched the secret exactly.
    """

    secret: Code
    guesses: Tuple[Code, ...]
    feedbacks: Tuple[Feedback, ...]
    current: Code
    max_guesses: int = MAX_GUESSES
    game_over: bool = False
    won: bool = False


def new_game(rng: random.Random) -> GameState:
    """Start a fresh game with a randomly generated secret code.

    Each peg is an independent draw from ``1..NUM_COLORS`` (duplicates allowed),
    so a four-peg, six-color game has ``6 ** 4`` possible secrets.
    """
    secret: Code = tuple(rng.randint(1, NUM_COLORS) for _ in range(CODE_LENGTH))
    return GameState(
        secret=secret,
        guesses=(),
        feedbacks=(),
        current=(),
    )


# ---------------------------------------------------------------------------
# Feedback scoring
# ---------------------------------------------------------------------------

def score_guess(secret: Code, guess: Code) -> Feedback:
    """Return ``(exact, partial)`` feedback for *guess* against *secret*.

    ``exact`` counts pegs with the correct color in the correct position.
    ``partial`` counts pegs whose color appears in the secret but in a different
    position, without ever reusing a secret peg that an exact match already
    consumed.

    Duplicate colors are handled by counting, not by per-position flags: the
    total number of color matches (ignoring position) is
    ``sum(min(secret_count[c], guess_count[c]) for c in colors)``, and the
    partial count is that total minus the exact matches. This guarantees a
    repeated color in the guess is never credited more times than it occurs in
    the secret.
    """
    assert len(secret) == len(guess)

    exact = sum(1 for s, g in zip(secret, guess) if s == g)

    secret_counts = Counter(secret)
    guess_counts = Counter(guess)
    color_matches = sum(
        min(secret_counts[color], guess_counts[color]) for color in guess_counts
    )

    partial = color_matches - exact
    return (exact, partial)


# ---------------------------------------------------------------------------
# State transitions
# ---------------------------------------------------------------------------

def set_peg(state: GameState, color: int) -> GameState:
    """Append *color* to the current guess if there is room.

    Ignores out-of-range colors and input once the row is full or the game is
    over, returning the same state object so the loop can skip redrawing.
    """
    if state.game_over or len(state.current) >= CODE_LENGTH:
        return state
    if not 1 <= color <= NUM_COLORS:
        return state
    return replace(state, current=state.current + (color,))


def delete_peg(state: GameState) -> GameState:
    """Remove the last peg from the current guess."""
    if state.game_over or not state.current:
        return state
    return replace(state, current=state.current[:-1])


def submit_guess(state: GameState) -> GameState:
    """Score the current guess and append it once the row is full.

    Returns the same state object when the game is over or the row is not yet
    complete, so the caller can tell nothing changed. On success the guess and
    its feedback are recorded, the input row is cleared, and win/loss flags are
    updated.
    """
    if state.game_over or len(state.current) < CODE_LENGTH:
        return state

    guess = state.current
    feedback = score_guess(state.secret, guess)
    guesses = state.guesses + (guess,)
    feedbacks = state.feedbacks + (feedback,)

    won = feedback[0] == CODE_LENGTH
    game_over = won or len(guesses) >= state.max_guesses

    return replace(
        state,
        guesses=guesses,
        feedbacks=feedbacks,
        current=(),
        game_over=game_over,
        won=won,
    )

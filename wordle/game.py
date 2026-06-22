"""Immutable game state and the transitions that drive a game of Wordle.

Every transition takes a :class:`GameState` and returns a new one, so the game
loop can compare object identity to tell whether anything actually changed.
Randomness lives outside the state: new_game receives a ``random.Random`` so
the state itself stays a pure value.
"""
from __future__ import annotations

import random
from collections import Counter
from dataclasses import dataclass, replace
from enum import Enum, auto
from typing import Tuple

from words import WORDS

WORD_LENGTH = 5
MAX_TRIES = 6


class Score(Enum):
    """Result for a single letter position after scoring a guess."""
    GREEN = auto()   # correct letter, correct position
    YELLOW = auto()  # correct letter, wrong position
    GRAY = auto()    # letter not in the word (or exhausted its count)


# A row of per-letter scores.
ScoreRow = Tuple[Score, ...]


@dataclass(frozen=True)
class GameState:
    """Complete, immutable state of one Wordle round."""

    answer: str
    guesses: Tuple[str, ...]        # submitted words, up to MAX_TRIES
    scores: Tuple[ScoreRow, ...]    # parallel to guesses
    current: str                    # letters typed so far for the next guess
    game_over: bool
    won: bool
    notice: str                     # brief one-line message to the player


def new_game(rng: random.Random) -> GameState:
    """Start a fresh game with an answer drawn from the word list."""
    answer = rng.choice(WORDS)
    return GameState(
        answer=answer,
        guesses=(),
        scores=(),
        current="",
        game_over=False,
        won=False,
        notice="",
    )


# ---------------------------------------------------------------------------
# Scoring
# ---------------------------------------------------------------------------

def score_guess(answer: str, guess: str) -> ScoreRow:
    """Score each letter of *guess* against *answer* using the standard Wordle
    algorithm.

    Pass 1: assign GREEN to positions where letter matches exactly, and
    decrement those letters from the remaining-count pool.
    Pass 2: assign YELLOW if the letter still has remaining count in the pool,
    otherwise GRAY. Extra duplicates beyond the answer's count become GRAY.
    """
    assert len(answer) == WORD_LENGTH and len(guess) == WORD_LENGTH

    result: list[Score | None] = [None] * WORD_LENGTH
    remaining = Counter(answer)

    # Pass 1: greens
    for i, (a, g) in enumerate(zip(answer, guess)):
        if g == a:
            result[i] = Score.GREEN
            remaining[g] -= 1

    # Pass 2: yellows and grays
    for i, g in enumerate(guess):
        if result[i] is not None:
            continue  # already green
        if remaining[g] > 0:
            result[i] = Score.YELLOW
            remaining[g] -= 1
        else:
            result[i] = Score.GRAY

    return tuple(result)  # type: ignore[return-value]


# ---------------------------------------------------------------------------
# State transitions
# ---------------------------------------------------------------------------

def type_letter(state: GameState, letter: str) -> GameState:
    """Append *letter* to the current input if there is room."""
    if state.game_over or len(state.current) >= WORD_LENGTH:
        return state
    return replace(state, current=state.current + letter.upper(), notice="")


def delete_letter(state: GameState) -> GameState:
    """Remove the last typed letter from the current input."""
    if state.game_over or not state.current:
        return state
    return replace(state, current=state.current[:-1], notice="")


def submit_guess(state: GameState) -> GameState:
    """Validate and score the current 5-letter input.

    Returns an unchanged state (with a notice) if the guess is not ready.
    On success returns a new state with the scored guess appended.
    """
    if state.game_over:
        return state
    if len(state.current) < WORD_LENGTH:
        return replace(state, notice="Not enough letters")

    guess = state.current
    row = score_guess(state.answer, guess)
    guesses = state.guesses + (guess,)
    scores = state.scores + (row,)

    won = all(s == Score.GREEN for s in row)
    game_over = won or len(guesses) >= MAX_TRIES

    return replace(
        state,
        guesses=guesses,
        scores=scores,
        current="",
        game_over=game_over,
        won=won,
        notice="",
    )

"""Headless logic checks for the Wordle core (no terminal required).

Run with ``python selftest.py``. Exercises scoring (including duplicate-letter
edge cases), state transitions, immutability, the word list, and render string
composition so the game can be verified in CI or over SSH without a TTY.
"""
from __future__ import annotations

import io
import random
from contextlib import redirect_stdout

import game as G
from game import Score
from words import WORDS, validate_word_list


def check(condition: bool, label: str) -> None:
    if not condition:
        raise AssertionError(f"FAILED: {label}")
    print(f"ok - {label}")


# ---------------------------------------------------------------------------
# Word list
# ---------------------------------------------------------------------------

def test_word_list() -> None:
    check(len(WORDS) > 0, "word list is non-empty")
    check(all(len(w) == 5 for w in WORDS), "every word in the list is length 5")
    check(all(w.isupper() for w in WORDS), "every word is uppercase")
    check(all(w.isalpha() for w in WORDS), "every word is alpha-only")
    check(all("Q" not in w for w in WORDS), "no word contains Q (reserved for quit)")
    validate_word_list()  # raises ValueError on any violation
    check(True, "validate_word_list() passes without error")


# ---------------------------------------------------------------------------
# Scoring algorithm
# ---------------------------------------------------------------------------

def test_score_all_green() -> None:
    row = G.score_guess("CRANE", "CRANE")
    check(
        row == (Score.GREEN,) * 5,
        "exact match scores all GREEN",
    )


def test_score_all_gray() -> None:
    row = G.score_guess("CRANE", "PILOT")
    check(
        all(s == Score.GRAY for s in row),
        "no shared letters scores all GRAY",
    )


def test_score_duplicate_alloy_lolly() -> None:
    # answer=ALLOY, guess=LOLLY
    # A L L O Y
    # L O L L Y
    # pos0: L vs A -> not green; A has no L at pos0
    # pos1: O vs L -> not green
    # pos2: L vs L -> GREEN; remaining L count: ALLOY has 2 L's -> after green at pos2, remaining={A:1,L:1,O:1,Y:1}
    # pos3: L vs L -> not green (pos3 of ALLOY is O); remaining L=1 -> YELLOW
    # pos4: Y vs Y -> GREEN
    # Pass2 for pos0 (L): remaining[L]=1 -> YELLOW, remaining[L]=0
    # Pass2 for pos1 (O): remaining[O]=1 -> YELLOW, remaining[O]=0
    # Pass2 for pos3 (L): remaining[L]=0 -> GRAY
    # Expected: YELLOW YELLOW GREEN GRAY GREEN
    row = G.score_guess("ALLOY", "LOLLY")
    expected = (Score.YELLOW, Score.YELLOW, Score.GREEN, Score.GRAY, Score.GREEN)
    check(
        row == expected,
        f"ALLOY/LOLLY duplicate-L: got {row}, expected {expected}",
    )


def test_score_duplicate_abbey_kebab() -> None:
    # answer=ABBEY, guess=KEBAB
    # A B B E Y
    # K E B A B
    # pos0: K vs A -> not green
    # pos1: E vs B -> not green
    # pos2: B vs B -> GREEN; remaining after greens: ABBEY has A:1,B:2,E:1,Y:1; pos2 green -> remaining B=1
    # pos3: A vs E -> not green
    # pos4: B vs Y -> not green
    # Pass2:
    # pos0 K: remaining[K]=0 -> GRAY
    # pos1 E: remaining[E]=1 -> YELLOW
    # pos3 A: remaining[A]=1 -> YELLOW
    # pos4 B: remaining[B]=1 -> YELLOW
    # Expected: GRAY YELLOW GREEN YELLOW YELLOW
    row = G.score_guess("ABBEY", "KEBAB")
    expected = (Score.GRAY, Score.YELLOW, Score.GREEN, Score.YELLOW, Score.YELLOW)
    check(
        row == expected,
        f"ABBEY/KEBAB duplicate-B: got {row}, expected {expected}",
    )


def test_score_single_duplicate_exhausted() -> None:
    # answer=BANAL, guess=LLAMA  (answer has one L at pos4)
    # B A N A L
    # L L A M A
    # Greens: none (B!=L, A!=L, N!=A, A!=M, L!=A)
    # remaining = Counter(BANAL) = {B:1,A:2,N:1,L:1}
    # Pass2:
    # pos0 L: remaining[L]=1 -> YELLOW, remaining[L]=0
    # pos1 L: remaining[L]=0 -> GRAY
    # pos2 A: remaining[A]=2 -> YELLOW, remaining[A]=1
    # pos3 M: remaining[M]=0 -> GRAY
    # pos4 A: remaining[A]=1 -> YELLOW, remaining[A]=0
    # Expected: YELLOW GRAY YELLOW GRAY YELLOW
    row = G.score_guess("BANAL", "LLAMA")
    expected = (Score.YELLOW, Score.GRAY, Score.YELLOW, Score.GRAY, Score.YELLOW)
    check(
        row == expected,
        f"BANAL/LLAMA single-L exhausted: got {row}, expected {expected}",
    )


# ---------------------------------------------------------------------------
# State transitions and immutability
# ---------------------------------------------------------------------------

def test_type_letter_immutability() -> None:
    rng = random.Random(42)
    state = G.new_game(rng)
    new_state = G.type_letter(state, "A")
    check(state.current == "", "original state is unchanged after type_letter")
    check(new_state.current == "A", "new state has the typed letter appended")
    check(new_state is not state, "type_letter returns a new state object")


def test_type_letter_max_length() -> None:
    rng = random.Random(42)
    state = G.new_game(rng)
    for ch in "ABCDE":
        state = G.type_letter(state, ch)
    check(len(state.current) == 5, "current input is 5 letters after typing 5")
    extra = G.type_letter(state, "F")
    check(extra is state, "typing beyond 5 letters returns the same state")


def test_delete_letter() -> None:
    rng = random.Random(42)
    state = G.new_game(rng)
    state = G.type_letter(state, "A")
    state = G.type_letter(state, "B")
    deleted = G.delete_letter(state)
    check(deleted.current == "A", "delete removes the last typed letter")
    check(deleted is not state, "delete_letter returns a new state object")


def test_delete_letter_empty() -> None:
    rng = random.Random(42)
    state = G.new_game(rng)
    same = G.delete_letter(state)
    check(same is state, "deleting from empty input returns the same state")


def test_submit_incomplete_guess() -> None:
    rng = random.Random(42)
    state = G.new_game(rng)
    state = G.type_letter(state, "A")
    submitted = G.submit_guess(state)
    check(submitted.notice != "", "submitting fewer than 5 letters sets a notice")
    check(len(submitted.guesses) == 0, "incomplete guess is not recorded")


def test_submit_guess_records_result() -> None:
    rng = random.Random(42)
    state = G.new_game(rng)
    # Type 5 letters and submit.
    for ch in "CRANE":
        state = G.type_letter(state, ch)
    submitted = G.submit_guess(state)
    check(len(submitted.guesses) == 1, "submitted guess is recorded")
    check(len(submitted.scores) == 1, "score row is recorded")
    check(submitted.current == "", "current input cleared after submit")


# ---------------------------------------------------------------------------
# Win and lose conditions
# ---------------------------------------------------------------------------

def test_exact_guess_wins() -> None:
    rng = random.Random(99)
    state = G.new_game(rng)
    answer = state.answer
    for ch in answer:
        state = G.type_letter(state, ch)
    state = G.submit_guess(state)
    check(state.won, "guessing the answer sets won=True")
    check(state.game_over, "guessing the answer sets game_over=True")
    check(
        all(s == Score.GREEN for s in state.scores[0]),
        "winning guess scores all GREEN",
    )


def test_six_wrong_guesses_loses() -> None:
    rng = random.Random(7)
    state = G.new_game(rng)
    answer = state.answer

    # Build 6 wrong words that are 5 alpha chars and not the answer.
    wrong_words = [w for w in WORDS if w != answer]
    # Use the first 6 words from the list (they may or may not share letters;
    # what matters is that none equals the answer).
    for i in range(G.MAX_TRIES):
        for ch in wrong_words[i]:
            state = G.type_letter(state, ch)
        state = G.submit_guess(state)
        if state.won:
            # Unlikely but if one of the wrong_words accidentally IS the answer
            # (shouldn't happen since we filtered), skip this seed's edge case.
            break

    check(not state.won, "six wrong guesses does not set won")
    check(state.game_over, "six wrong guesses sets game_over=True")
    check(len(state.guesses) == G.MAX_TRIES, "exactly MAX_TRIES guesses recorded")
    # The answer must be accessible on the state so the renderer can reveal it.
    check(state.answer == answer, "answer is preserved in final state for reveal")


def test_no_action_after_game_over() -> None:
    rng = random.Random(99)
    state = G.new_game(rng)
    answer = state.answer
    for ch in answer:
        state = G.type_letter(state, ch)
    state = G.submit_guess(state)
    assert state.game_over

    same = G.type_letter(state, "A")
    check(same is state, "type_letter after game_over returns same state")
    same2 = G.delete_letter(state)
    check(same2 is state, "delete_letter after game_over returns same state")
    same3 = G.submit_guess(state)
    check(same3 is state, "submit_guess after game_over returns same state")


# ---------------------------------------------------------------------------
# Render / draw composition (no TTY required)
# ---------------------------------------------------------------------------

def test_render_builds_strings() -> None:
    from blessed import Terminal
    import render as R

    term = Terminal(force_styling=True)
    rng = random.Random(4)
    state = G.new_game(rng)

    blines = R.board_lines(term, state)
    check(len(blines) == G.MAX_TRIES, "board_lines returns one line per try row")

    plines = R.panel_lines(term, state)
    check(any("WORDLE" in line for line in plines), "panel shows the WORDLE title")

    # Type some letters to exercise the active-row tile path.
    for ch in "CRANE":
        state = G.type_letter(state, ch)
    blines_active = R.board_lines(term, state)
    check(len(blines_active) == G.MAX_TRIES, "board_lines with active row has correct length")

    # draw() must compose a full frame (normal, win, lose) without raising.
    won_state = G.GameState(
        answer=state.answer,
        guesses=(state.answer,),
        scores=(tuple(Score.GREEN for _ in range(G.WORD_LENGTH)),),
        current="",
        game_over=True,
        won=True,
        notice="",
    )
    lost_state = G.GameState(
        answer=state.answer,
        guesses=tuple("CRANE" for _ in range(G.MAX_TRIES)),
        scores=tuple(
            G.score_guess(state.answer, "CRANE") for _ in range(G.MAX_TRIES)
        ),
        current="",
        game_over=True,
        won=False,
        notice="",
    )

    with redirect_stdout(io.StringIO()):
        R.draw(term, state)
        R.draw(term, won_state)
        R.draw(term, lost_state)
    check(True, "draw() composes normal, won, and lost frames without error")


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------

def main() -> None:
    tests = [
        test_word_list,
        test_score_all_green,
        test_score_all_gray,
        test_score_duplicate_alloy_lolly,
        test_score_duplicate_abbey_kebab,
        test_score_single_duplicate_exhausted,
        test_type_letter_immutability,
        test_type_letter_max_length,
        test_delete_letter,
        test_delete_letter_empty,
        test_submit_incomplete_guess,
        test_submit_guess_records_result,
        test_exact_guess_wins,
        test_six_wrong_guesses_loses,
        test_no_action_after_game_over,
        test_render_builds_strings,
    ]
    for test in tests:
        test()
    print(f"\nAll {len(tests)} test groups passed.")


if __name__ == "__main__":
    main()

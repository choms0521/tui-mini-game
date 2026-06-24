"""Headless logic checks for the Mastermind core (no terminal required).

Run with ``python selftest.py``. Exercises feedback scoring (with a heavy focus
on duplicate-color edge cases), state transitions, immutability, win/loss
detection, deterministic secret generation, and render string composition so the
game can be verified in CI or over SSH without a TTY.
"""
from __future__ import annotations

import dataclasses
import io
import random
from contextlib import redirect_stdout

import game as G


def check(condition: bool, label: str) -> None:
    if not condition:
        raise AssertionError(f"FAILED: {label}")
    print(f"ok - {label}")


# ---------------------------------------------------------------------------
# New-game state and deterministic secret generation
# ---------------------------------------------------------------------------

def test_new_game_initial_state() -> None:
    rng = random.Random(42)
    state = G.new_game(rng)
    check(len(state.secret) == G.CODE_LENGTH, "secret has CODE_LENGTH pegs")
    check(all(1 <= peg <= G.NUM_COLORS for peg in state.secret), "every peg is a valid color")
    check(state.guesses == (), "no guesses at start")
    check(state.feedbacks == (), "no feedback at start")
    check(state.current == (), "input row is empty at start")
    check(not state.game_over, "game does not start over")
    check(not state.won, "game does not start won")


def test_secret_deterministic() -> None:
    # Same seed reproduces the same secret. We intentionally avoid asserting that
    # two arbitrary seeds differ: that would rely on the seeds not colliding
    # (1 / NUM_COLORS**CODE_LENGTH) and proves nothing about new_game's contract.
    # test_new_game_uses_injected_rng verifies RNG usage robustly instead.
    s1 = G.new_game(random.Random(123)).secret
    s2 = G.new_game(random.Random(123)).secret
    check(s1 == s2, "same seed produces the same secret")


def test_new_game_uses_injected_rng() -> None:
    """new_game must derive the secret from the injected RNG.

    A recording fake proves the dependency directly instead of relying on two
    arbitrary seeds happening to produce different secrets, which is brittle and
    tests no real contract.
    """
    class RecordingRandom:
        def __init__(self, values: list[int]) -> None:
            self._values = list(values)
            self.calls: list[tuple[int, int]] = []

        def randint(self, a: int, b: int) -> int:
            self.calls.append((a, b))
            return self._values.pop(0)

    sequence = [1, 2, 3, 4]
    fake = RecordingRandom(sequence)
    state = G.new_game(fake)
    check(state.secret == tuple(sequence), "secret is built from the injected RNG's draws")
    check(len(fake.calls) == G.CODE_LENGTH, "new_game draws exactly CODE_LENGTH times")
    check(
        all(call == (1, G.NUM_COLORS) for call in fake.calls),
        "each draw spans the full color range 1..NUM_COLORS",
    )


# ---------------------------------------------------------------------------
# Feedback scoring -- exact and partial
# ---------------------------------------------------------------------------

def test_score_all_exact() -> None:
    fb = G.score_guess((1, 2, 3, 4), (1, 2, 3, 4))
    check(fb == (4, 0), "identical guess scores (4, 0)")


def test_score_all_miss() -> None:
    fb = G.score_guess((1, 1, 1, 1), (2, 2, 2, 2))
    check(fb == (0, 0), "no shared colors scores (0, 0)")


def test_score_all_partial() -> None:
    # Same multiset, every peg in the wrong position.
    fb = G.score_guess((1, 2, 3, 4), (4, 3, 2, 1))
    check(fb == (0, 4), "fully permuted guess scores (0, 4)")


def test_score_mixed_no_duplicates() -> None:
    # secret 1 2 3 4 ; guess 1 3 2 5
    # exact: pos0 (1) -> 1 ; color matches: 1,2,3 present -> 3 ; partial = 3 - 1 = 2
    fb = G.score_guess((1, 2, 3, 4), (1, 3, 2, 5))
    check(fb == (1, 2), "mixed guess without duplicates scores (1, 2)")


# ---------------------------------------------------------------------------
# Feedback scoring -- duplicate-color edge cases (the #1 correctness risk)
# ---------------------------------------------------------------------------

def test_dup_secret_and_guess() -> None:
    # secret 1 1 2 2 ; guess 1 2 2 3
    # exact: pos0 (1), pos2 (2) -> 2
    # color matches: c1 min(2,1)=1, c2 min(2,2)=2, c3 min(0,1)=0 -> 3
    # partial = 3 - 2 = 1
    fb = G.score_guess((1, 1, 2, 2), (1, 2, 2, 3))
    check(fb == (2, 1), "secret=(1,1,2,2) guess=(1,2,2,3) scores (2, 1)")


def test_dup_guess_not_overcounted() -> None:
    # secret 1 2 3 4 ; guess 1 1 1 1
    # exact: pos0 (1) -> 1
    # color matches: c1 min(1,4)=1 -> 1 ; partial = 1 - 1 = 0
    fb = G.score_guess((1, 2, 3, 4), (1, 1, 1, 1))
    check(fb == (1, 0), "repeated guess color is credited at most secret's count")


def test_dup_secret_limits_partials() -> None:
    # secret 1 1 1 1 ; guess 1 1 2 2
    # exact: pos0, pos1 -> 2
    # color matches: c1 min(4,2)=2 -> 2 ; partial = 2 - 2 = 0
    fb = G.score_guess((1, 1, 1, 1), (1, 1, 2, 2))
    check(fb == (2, 0), "no partials when all color matches are already exact")


def test_dup_partial_when_misplaced() -> None:
    # secret 1 1 2 3 ; guess 2 1 1 4
    # exact: pos1 (1) -> 1
    # color matches: c1 min(2,2)=2, c2 min(1,1)=1, c4 min(0,1)=0 -> 3
    # partial = 3 - 1 = 2
    fb = G.score_guess((1, 1, 2, 3), (2, 1, 1, 4))
    check(fb == (1, 2), "duplicate color split across exact and partial")


def test_dup_more_in_guess_than_secret() -> None:
    # secret 5 5 1 2 ; guess 5 5 5 5
    # exact: pos0, pos1 -> 2
    # color matches: c5 min(2,4)=2 -> 2 ; partial = 2 - 2 = 0
    fb = G.score_guess((5, 5, 1, 2), (5, 5, 5, 5))
    check(fb == (2, 0), "extra guess duplicates beyond secret's count score nothing")


def test_score_symmetry_total_never_exceeds_length() -> None:
    # Brute-force property: exact + partial <= CODE_LENGTH for all pairs.
    rng = random.Random(7)
    for _ in range(500):
        secret = tuple(rng.randint(1, G.NUM_COLORS) for _ in range(G.CODE_LENGTH))
        guess = tuple(rng.randint(1, G.NUM_COLORS) for _ in range(G.CODE_LENGTH))
        exact, partial = G.score_guess(secret, guess)
        if not (exact >= 0 and partial >= 0 and exact + partial <= G.CODE_LENGTH):
            raise AssertionError(
                f"FAILED: invalid feedback {exact, partial} for {secret} vs {guess}"
            )
    check(True, "exact+partial stays within [0, CODE_LENGTH] over 500 random pairs")


# ---------------------------------------------------------------------------
# State transitions and immutability
# ---------------------------------------------------------------------------

def test_set_peg_appends() -> None:
    state = G.new_game(random.Random(1))
    new_state = G.set_peg(state, 3)
    check(state.current == (), "original state is unchanged after set_peg")
    check(new_state.current == (3,), "new state has the placed color appended")
    check(new_state is not state, "set_peg returns a new state object")


def test_set_peg_rejects_out_of_range() -> None:
    state = G.new_game(random.Random(1))
    check(G.set_peg(state, 0) is state, "color 0 is rejected")
    check(G.set_peg(state, G.NUM_COLORS + 1) is state, "color above range is rejected")


def test_set_peg_full_row() -> None:
    state = G.new_game(random.Random(1))
    for _ in range(G.CODE_LENGTH):
        state = G.set_peg(state, 1)
    check(len(state.current) == G.CODE_LENGTH, "input fills to CODE_LENGTH pegs")
    extra = G.set_peg(state, 2)
    check(extra is state, "placing beyond a full row returns the same state")


def test_delete_peg() -> None:
    state = G.new_game(random.Random(1))
    state = G.set_peg(state, 1)
    state = G.set_peg(state, 2)
    deleted = G.delete_peg(state)
    check(deleted.current == (1,), "delete removes the last placed peg")
    check(deleted is not state, "delete_peg returns a new state object")


def test_delete_peg_empty() -> None:
    state = G.new_game(random.Random(1))
    same = G.delete_peg(state)
    check(same is state, "deleting from an empty row returns the same state")


def test_submit_incomplete_guess() -> None:
    state = G.new_game(random.Random(1))
    state = G.set_peg(state, 1)
    submitted = G.submit_guess(state)
    check(submitted is state, "submitting an incomplete row returns the same state")
    check(len(submitted.guesses) == 0, "incomplete guess is not recorded")


def test_submit_records_result() -> None:
    state = dataclasses.replace(G.new_game(random.Random(1)), secret=(1, 2, 3, 4))
    for color in (5, 5, 5, 5):
        state = G.set_peg(state, color)
    submitted = G.submit_guess(state)
    check(len(submitted.guesses) == 1, "submitted guess is recorded")
    check(len(submitted.feedbacks) == 1, "feedback row is recorded")
    check(submitted.feedbacks[0] == (0, 0), "feedback matches the scored guess")
    check(submitted.current == (), "input row cleared after submit")


# ---------------------------------------------------------------------------
# Win and loss detection
# ---------------------------------------------------------------------------

def test_exact_guess_wins() -> None:
    state = dataclasses.replace(G.new_game(random.Random(1)), secret=(1, 2, 3, 4))
    for color in (1, 2, 3, 4):
        state = G.set_peg(state, color)
    state = G.submit_guess(state)
    check(state.won, "guessing the secret sets won=True")
    check(state.game_over, "guessing the secret sets game_over=True")
    check(state.feedbacks[-1] == (G.CODE_LENGTH, 0), "winning guess scores all exact")


def test_loss_after_max_guesses() -> None:
    state = dataclasses.replace(G.new_game(random.Random(1)), secret=(1, 1, 1, 1))
    # Submit MAX_GUESSES wrong guesses (all 2s never match the all-1s secret).
    for _ in range(G.MAX_GUESSES):
        for _ in range(G.CODE_LENGTH):
            state = G.set_peg(state, 2)
        state = G.submit_guess(state)
    check(not state.won, "running out of guesses does not set won")
    check(state.game_over, "running out of guesses sets game_over=True")
    check(len(state.guesses) == G.MAX_GUESSES, "exactly MAX_GUESSES guesses recorded")


def test_no_action_after_game_over() -> None:
    state = dataclasses.replace(G.new_game(random.Random(1)), secret=(1, 2, 3, 4))
    for color in (1, 2, 3, 4):
        state = G.set_peg(state, color)
    state = G.submit_guess(state)
    assert state.game_over

    check(G.set_peg(state, 1) is state, "set_peg after game_over returns the same state")
    check(G.delete_peg(state) is state, "delete_peg after game_over returns the same state")
    check(G.submit_guess(state) is state, "submit_guess after game_over returns the same state")


# ---------------------------------------------------------------------------
# Immutability of submit
# ---------------------------------------------------------------------------

def test_submit_immutability() -> None:
    state = dataclasses.replace(G.new_game(random.Random(1)), secret=(1, 2, 3, 4))
    for color in (1, 1, 1, 1):
        state = G.set_peg(state, color)
    original_current = state.current
    original_guesses = state.guesses
    new_state = G.submit_guess(state)
    check(new_state is not state, "submit_guess returns a new state object")
    check(state.current == original_current, "original input row is unchanged")
    check(state.guesses == original_guesses, "original guesses tuple is unchanged")


# ---------------------------------------------------------------------------
# Render / draw composition (no TTY required)
# ---------------------------------------------------------------------------

def test_render_builds_strings() -> None:
    from blessed import Terminal
    import render as R

    term = Terminal(force_styling=True)
    state = dataclasses.replace(G.new_game(random.Random(1)), secret=(1, 2, 3, 4))

    blines = R.board_lines(term, state)
    check(len(blines) == state.max_guesses, "board_lines returns one line per guess row")

    plines = R.panel_lines(term, state)
    check(any("MASTERMIND" in line for line in plines), "panel shows the MASTERMIND title")

    # Place some pegs to exercise the active-row path.
    for color in (1, 2):
        state = G.set_peg(state, color)
    blines_active = R.board_lines(term, state)
    check(len(blines_active) == state.max_guesses, "active-row board has the correct length")

    # Submit a guess so a feedback row is rendered.
    for color in (3, 4):
        state = G.set_peg(state, color)
    played = G.submit_guess(state)

    won_state = dataclasses.replace(played, game_over=True, won=True)
    lost_state = dataclasses.replace(played, game_over=True, won=False)

    with redirect_stdout(io.StringIO()):
        R.draw(term, played)
        R.draw(term, won_state)
        R.draw(term, lost_state)
    check(True, "draw() composes normal, won, and lost frames without error")


def test_howto_panel_and_help() -> None:
    """Panel contains how-to summary, all lines fit PANEL_WIDTH, help overlay composes."""
    from blessed import Terminal
    import render as R

    term = Terminal(force_styling=True)
    state = G.new_game(random.Random(1))

    panel = R.panel_lines(term, state)
    check(any("MASTERMIND" in line for line in panel), "panel shows the title")
    check(any("추론" in line for line in panel), "panel shows the Korean how-to summary")
    check(
        all(term.length(line) <= R.PANEL_WIDTH for line in panel),
        "every panel line fits PANEL_WIDTH",
    )

    with redirect_stdout(io.StringIO()):
        R.draw(term, state, show_help=True)
    check(True, "draw(show_help=True) composes the help overlay without error")


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------

def main() -> None:
    tests = [
        test_new_game_initial_state,
        test_secret_deterministic,
        test_new_game_uses_injected_rng,
        test_score_all_exact,
        test_score_all_miss,
        test_score_all_partial,
        test_score_mixed_no_duplicates,
        test_dup_secret_and_guess,
        test_dup_guess_not_overcounted,
        test_dup_secret_limits_partials,
        test_dup_partial_when_misplaced,
        test_dup_more_in_guess_than_secret,
        test_score_symmetry_total_never_exceeds_length,
        test_set_peg_appends,
        test_set_peg_rejects_out_of_range,
        test_set_peg_full_row,
        test_delete_peg,
        test_delete_peg_empty,
        test_submit_incomplete_guess,
        test_submit_records_result,
        test_exact_guess_wins,
        test_loss_after_max_guesses,
        test_no_action_after_game_over,
        test_submit_immutability,
        test_render_builds_strings,
        test_howto_panel_and_help,
    ]
    for test in tests:
        test()
    print(f"\nAll {len(tests)} test groups passed.")


if __name__ == "__main__":
    main()

"""Headless logic checks for the Blackjack core (no terminal required).

Run with ``python selftest.py``. Exercises hand evaluation (Ace soft/hard),
blackjack detection and precedence, immediate natural resolution, bust
detection, dealer auto-play, comparison logic, deck dealing (no duplicates,
deterministic shuffle), immutability, and render string composition so the game
can be verified in CI or over SSH without a TTY.
"""
from __future__ import annotations

import io
import random
from contextlib import redirect_stdout
from dataclasses import replace

import cards as C
import game as G

# Convenient card constants. suit is irrelevant to value; pick distinct suits
# where a hand needs duplicate ranks so the cards are not equal tuples.
ACE_S = (1, 0)
ACE_H = (1, 1)
KING_S = (13, 0)
KING_C = (13, 3)
QUEEN_H = (12, 1)
TEN_D = (10, 2)
TEN_C = (10, 3)
EIGHT_C = (8, 3)
NINE_S = (9, 0)
NINE_H = (9, 1)
SIX_S = (6, 0)
FIVE_D = (5, 2)
FIVE_C = (5, 3)
SEVEN_S = (7, 0)
SEVEN_H = (7, 1)
SEVEN_C = (7, 3)
TWO_C = (2, 3)


def check(condition: bool, label: str) -> None:
    if not condition:
        raise AssertionError(f"FAILED: {label}")
    print(f"ok - {label}")


class _StackedDeck:
    """A ``random.Random`` stand-in whose ``shuffle`` stacks a known deck top.

    ``new_game`` deals player[0], dealer[0], player[1], dealer[1] from the front
    of the shuffled deck, so placing chosen cards at the front makes the initial
    deal deterministic without depending on a specific RNG implementation.
    """

    def __init__(self, front: tuple) -> None:
        self._front = list(front)

    def shuffle(self, seq: list) -> None:
        rest = [card for card in seq if card not in self._front]
        seq[:] = self._front + rest


# ---------------------------------------------------------------------------
# Hand value: Ace soft -> hard
# ---------------------------------------------------------------------------

def test_hand_value_ace_soft_hard() -> None:
    check(G.hand_value((ACE_S, KING_S)) == 21, "A+K counts the Ace as 11 -> 21")
    check(G.hand_value((ACE_S, ACE_H, NINE_S)) == 21, "A+A+9 -> 21 (one soft, one hard Ace)")
    check(
        G.hand_value((ACE_S, NINE_S, FIVE_D)) == 15,
        "A+9+5 downgrades the Ace to 1 -> 15 (soft to hard)",
    )
    check(G.hand_value((TEN_D, SEVEN_S)) == 17, "10+7 -> 17 (no Ace)")
    check(G.hand_value((ACE_S, ACE_H)) == 12, "A+A -> 12 (one Ace stays 11, one drops to 1)")
    check(G.hand_value((KING_S, QUEEN_H)) == 20, "K+Q -> 20 (faces score 10)")


# ---------------------------------------------------------------------------
# Blackjack detection and precedence
# ---------------------------------------------------------------------------

def test_is_blackjack() -> None:
    check(G.is_blackjack((ACE_S, KING_S)), "A+K is a natural blackjack")
    check(G.is_blackjack((ACE_S, TEN_D)), "A+10 is a natural blackjack")
    check(not G.is_blackjack((KING_S, QUEEN_H)), "K+Q (20) is not a blackjack")
    check(
        not G.is_blackjack((SEVEN_S, SEVEN_H, SEVEN_C)),
        "7+7+7 (21 from three cards) is not a blackjack",
    )


def test_blackjack_outranks_three_card_21() -> None:
    # Player has a natural 21; dealer reaches 21 with three cards. Player wins.
    player = (ACE_S, KING_S)                  # two-card 21 (blackjack)
    dealer = (SEVEN_S, SEVEN_H, SEVEN_C)      # three-card 21
    check(G.hand_value(dealer) == 21, "dealer three-card hand totals 21")
    check(not G.is_blackjack(dealer), "dealer three-card 21 is not a blackjack")
    check(
        G.resolve_result(player, dealer) == G.RESULT_BLACKJACK,
        "blackjack outranks a 3-card 21 (player wins with blackjack)",
    )


# ---------------------------------------------------------------------------
# Immediate natural resolution
# ---------------------------------------------------------------------------

def test_natural_resolution_both_blackjack_push() -> None:
    player = (ACE_S, KING_S)
    dealer = (ACE_H, QUEEN_H)
    check(
        G.resolve_result(player, dealer) == G.RESULT_PUSH,
        "both blackjack resolves to push",
    )


def test_natural_resolution_player_blackjack_wins() -> None:
    player = (ACE_S, KING_S)
    dealer = (TEN_D, NINE_S)   # ordinary 19
    check(
        G.resolve_result(player, dealer) == G.RESULT_BLACKJACK,
        "player-only blackjack wins",
    )


def test_natural_resolution_dealer_blackjack_wins() -> None:
    player = (TEN_D, NINE_S)   # ordinary 19
    dealer = (ACE_H, KING_S)
    check(
        G.resolve_result(player, dealer) == G.RESULT_LOSE,
        "dealer-only blackjack beats an ordinary player 19",
    )


def test_new_game_settles_naturals_immediately() -> None:
    # Stack the deck deterministically instead of scanning RNG seeds (whose
    # output is not guaranteed stable across Python implementations). new_game
    # deals player[0], dealer[0], player[1], dealer[1] from the front, so this
    # front gives the player a natural (A+K) and the dealer an ordinary 17 (9+8).
    rng = _StackedDeck((ACE_S, NINE_S, KING_S, EIGHT_C))
    state = G.new_game(rng)
    check(G.is_blackjack(state.player_hand), "the stacked deal gives the player a natural")
    check(state.game_over, "a natural at the deal sets game_over")
    check(state.phase == G.PHASE_RESULT, "a natural at the deal moves to the result phase")
    check(state.result is not None, "a natural at the deal has a result")


# ---------------------------------------------------------------------------
# Bust detection
# ---------------------------------------------------------------------------

def test_bust_detection() -> None:
    check(G.is_bust((KING_S, QUEEN_H, FIVE_D)), "10+10+5 = 25 is a bust")
    check(not G.is_bust((KING_S, QUEEN_H)), "10+10 = 20 is not a bust")
    check(not G.is_bust((ACE_S, KING_S, KING_C)), "A+K+K = 21 (soft Ace) is not a bust")


def test_hit_bust_settles_as_loss() -> None:
    # Player holds 20; the next card is a 5 which busts the hand.
    state = G.GameState(
        deck=(FIVE_D, TWO_C),
        player_hand=(KING_S, QUEEN_H),
        dealer_hand=(TEN_D, SIX_S),
        phase=G.PHASE_PLAYER,
        result=None,
        game_over=False,
    )
    after = G.hit(state)
    check(after.game_over, "hit into a bust sets game_over")
    check(after.result == G.RESULT_LOSE, "a player bust is always a loss")
    check(after.phase == G.PHASE_RESULT, "a bust moves to the result phase")
    check(len(after.dealer_hand) == 2, "the dealer never draws after a player bust")


# ---------------------------------------------------------------------------
# Dealer auto-play
# ---------------------------------------------------------------------------

def test_dealer_hits_until_17() -> None:
    # Dealer holds 16 (10+6); the deck front is a 5 -> dealer reaches 21 and stands.
    state = G.GameState(
        deck=(FIVE_D, TWO_C, SEVEN_S),
        player_hand=(KING_S, QUEEN_H),   # 20, no natural
        dealer_hand=(TEN_D, SIX_S),
        phase=G.PHASE_PLAYER,
        result=None,
        game_over=False,
    )
    after = G.stand(state)
    check(G.hand_value(after.dealer_hand) == 21, "dealer draws from 16 to 21")
    check(after.result == G.RESULT_LOSE, "dealer 21 beats player 20")


def test_dealer_stands_on_soft_17() -> None:
    # Dealer holds soft 17 (A+6). Policy: stand. If it (wrongly) hit, the front
    # card would change the hand, so we assert the hand is untouched.
    state = G.GameState(
        deck=(FIVE_D, TWO_C),
        player_hand=(TEN_D, SEVEN_S),    # 17, no natural
        dealer_hand=(ACE_S, SIX_S),      # soft 17
        phase=G.PHASE_PLAYER,
        result=None,
        game_over=False,
    )
    after = G.stand(state)
    check(len(after.dealer_hand) == 2, "dealer stands on soft 17 (no extra card)")
    check(G.hand_value(after.dealer_hand) == 17, "dealer soft-17 value stays 17")
    check(after.result == G.RESULT_PUSH, "player 17 vs dealer 17 is a push")


def test_dealer_busts_player_wins() -> None:
    # Dealer holds 16; the front card is a 10 -> dealer busts at 26.
    state = G.GameState(
        deck=(TEN_D, TWO_C),
        player_hand=(KING_S, SEVEN_S),   # 17, no natural
        dealer_hand=(TEN_C, SIX_S),      # 16
        phase=G.PHASE_PLAYER,
        result=None,
        game_over=False,
    )
    after = G.stand(state)
    check(G.is_bust(after.dealer_hand), "dealer busts drawing the 10")
    check(after.result == G.RESULT_WIN, "a dealer bust makes the player win")


# ---------------------------------------------------------------------------
# Comparison logic
# ---------------------------------------------------------------------------

def test_comparison_logic() -> None:
    check(
        G.resolve_result((KING_S, QUEEN_H), (TEN_D, NINE_S)) == G.RESULT_WIN,
        "player 20 vs dealer 19 -> win",
    )
    check(
        G.resolve_result((TEN_D, NINE_S), (KING_S, QUEEN_H)) == G.RESULT_LOSE,
        "player 19 vs dealer 20 -> lose",
    )
    check(
        G.resolve_result((KING_S, QUEEN_H), (TEN_D, TEN_C)) == G.RESULT_PUSH,
        "player 20 vs dealer 20 -> push",
    )
    check(
        G.resolve_result((KING_S, QUEEN_H), (TEN_D, SIX_S, EIGHT_C)) == G.RESULT_WIN,
        "dealer bust (24) -> player wins",
    )
    check(
        G.resolve_result((KING_S, QUEEN_H, EIGHT_C), (TEN_D, NINE_S)) == G.RESULT_LOSE,
        "player bust always loses regardless of dealer total",
    )


# ---------------------------------------------------------------------------
# Deck dealing: no duplicates, deterministic shuffle
# ---------------------------------------------------------------------------

def test_deck_no_duplicates() -> None:
    state = G.new_game(random.Random(7))
    all_cards = list(state.deck) + list(state.player_hand) + list(state.dealer_hand)
    check(len(all_cards) == 52, "deck + hands account for all 52 cards")
    check(len(set(all_cards)) == 52, "no duplicate cards are dealt")
    check(set(all_cards) == set(C.full_deck()), "the dealt cards are exactly a full deck")


def test_shuffle_is_deterministic() -> None:
    a = G.new_game(random.Random(123))
    b = G.new_game(random.Random(123))
    check(a == b, "the same seed produces an identical initial state")
    c = G.new_game(random.Random(124))
    check(a != c, "a different seed produces a different deal")


def test_initial_deal_sizes() -> None:
    state = G.new_game(random.Random(1))
    check(len(state.player_hand) == 2, "player is dealt two cards")
    check(len(state.dealer_hand) == 2, "dealer is dealt two cards")
    check(len(state.deck) == 48, "48 cards remain in the deck after the deal")


# ---------------------------------------------------------------------------
# Immutability
# ---------------------------------------------------------------------------

def test_hit_immutability() -> None:
    deck = (FIVE_D, TWO_C, SEVEN_S)
    player = (NINE_H, SEVEN_C)
    dealer = (TEN_D, SIX_S)
    state = G.GameState(
        deck=deck, player_hand=player, dealer_hand=dealer,
        phase=G.PHASE_PLAYER, result=None, game_over=False,
    )
    after = G.hit(state)
    check(after is not state, "hit returns a new state object")
    check(state.player_hand == player, "original player_hand is unchanged after hit")
    check(state.deck == deck, "original deck is unchanged after hit")
    check(len(after.player_hand) == 3, "new state has the drawn card appended")


def test_stand_immutability() -> None:
    deck = (FIVE_D, TWO_C, SEVEN_S)
    player = (KING_S, QUEEN_H)
    dealer = (TEN_D, SIX_S)
    state = G.GameState(
        deck=deck, player_hand=player, dealer_hand=dealer,
        phase=G.PHASE_PLAYER, result=None, game_over=False,
    )
    after = G.stand(state)
    check(after is not state, "stand returns a new state object")
    check(state.dealer_hand == dealer, "original dealer_hand is unchanged after stand")
    check(state.deck == deck, "original deck is unchanged after stand")


def test_no_action_after_game_over() -> None:
    state = G.GameState(
        deck=(FIVE_D,), player_hand=(KING_S, QUEEN_H), dealer_hand=(TEN_D, NINE_S),
        phase=G.PHASE_RESULT, result=G.RESULT_WIN, game_over=True,
    )
    check(G.hit(state) is state, "hit after game_over returns the same state")
    check(G.stand(state) is state, "stand after game_over returns the same state")


# ---------------------------------------------------------------------------
# Render / draw composition (no TTY required)
# ---------------------------------------------------------------------------

def test_render_builds_strings() -> None:
    from blessed import Terminal
    import render as R

    term = Terminal(force_styling=True)
    state = G.new_game(random.Random(4))

    plines = R.panel_lines(term, state)
    check(any("BLACKJACK" in line for line in plines), "panel shows the BLACKJACK title")

    player_turn = G.GameState(
        deck=(), player_hand=(ACE_S, NINE_S), dealer_hand=(TEN_D, SIX_S),
        phase=G.PHASE_PLAYER, result=None, game_over=False,
    )
    result_frame = G.GameState(
        deck=(), player_hand=(ACE_S, KING_S), dealer_hand=(TEN_D, NINE_S),
        phase=G.PHASE_RESULT, result=G.RESULT_BLACKJACK, game_over=True,
    )

    with redirect_stdout(io.StringIO()):
        R.draw(term, player_turn)
        R.draw(term, result_frame)
    check(True, "draw() composes player-turn and result frames without error")


def test_render_panel_position_is_fixed() -> None:
    # The card area must use a fixed width so the panel does not drift as the
    # hand grows; otherwise hits would leave stale panel fragments behind.
    import render as R

    base = G.GameState(
        deck=(), player_hand=(ACE_S, FIVE_D), dealer_hand=(TEN_D, SIX_S),
        phase=G.PHASE_PLAYER, result=None, game_over=False,
    )
    two = base
    three = replace(base, player_hand=(ACE_S, FIVE_D, TWO_C))
    four = replace(base, player_hand=(ACE_S, FIVE_D, TWO_C, FIVE_C))

    # CONTENT_WIDTH is a module constant, so panel_x is independent of the hand.
    check(R.CONTENT_WIDTH == R._hand_width(R.LAYOUT_CARDS), "content width is the fixed layout width")
    # Each realistic hand must fit inside the fixed card area; because the area
    # never shrinks to the hand, the panel offset stays put as the hand grows.
    # Exercise the real _hand_width(n), not the constant, so a layout regression
    # would actually fail this check.
    for s in (two, three, four):
        n = len(s.player_hand)
        check(R._hand_width(n) <= R.CONTENT_WIDTH, f"a {n}-card hand fits within the fixed card area")
    check(
        R.CONTENT_WIDTH >= R._hand_width(4),
        "fixed width reserves room for at least a four-card hand",
    )


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------

def main() -> None:
    tests = [
        test_hand_value_ace_soft_hard,
        test_is_blackjack,
        test_blackjack_outranks_three_card_21,
        test_natural_resolution_both_blackjack_push,
        test_natural_resolution_player_blackjack_wins,
        test_natural_resolution_dealer_blackjack_wins,
        test_new_game_settles_naturals_immediately,
        test_bust_detection,
        test_hit_bust_settles_as_loss,
        test_dealer_hits_until_17,
        test_dealer_stands_on_soft_17,
        test_dealer_busts_player_wins,
        test_comparison_logic,
        test_deck_no_duplicates,
        test_shuffle_is_deterministic,
        test_initial_deal_sizes,
        test_hit_immutability,
        test_stand_immutability,
        test_no_action_after_game_over,
        test_render_builds_strings,
        test_render_panel_position_is_fixed,
    ]
    for test in tests:
        test()
    print(f"\nAll {len(tests)} test groups passed.")


if __name__ == "__main__":
    main()

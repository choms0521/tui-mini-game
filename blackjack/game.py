"""Immutable game state and the transitions that drive a game of Blackjack.

Every transition takes a :class:`GameState` and returns a new one via
``dataclasses.replace``, so the game loop can compare object identity to tell
whether anything actually changed. The deck, both hands, are tuples so a state
is a fully immutable value. Randomness lives outside the state: ``new_game``
receives a ``random.Random`` so the shuffle is deterministic in tests.

This module is pure logic only -- it never imports ``blessed``.
"""
from __future__ import annotations

import random
from dataclasses import dataclass, replace
from typing import Optional, Tuple

from cards import Card, card_value, full_deck

# Phases of a single hand. The dealer draws synchronously inside ``stand``, so a
# hand is only ever observably in "player" or "result" -- there is no separate
# dealer phase to model.
PHASE_PLAYER = "player"   # awaiting the player's hit/stand
PHASE_RESULT = "result"   # hand settled, result is final

# Result values.
RESULT_WIN = "win"           # player beats the dealer
RESULT_LOSE = "lose"         # dealer beats the player (or player bust)
RESULT_PUSH = "push"         # tie
RESULT_BLACKJACK = "blackjack"  # player wins with a natural 21

BLACKJACK_VALUE = 21
DEALER_STAND_MIN = 17        # dealer hits while the hand value is below this


@dataclass(frozen=True)
class GameState:
    """Complete, immutable state of one Blackjack hand.

    deck        -- remaining cards, dealt from the front (index 0).
    player_hand -- the player's cards.
    dealer_hand -- the dealer's cards; the second card is hidden during the
                   player's turn (a render-only concern, not stored here).
    phase       -- "player" or "result".
    result      -- "win" | "lose" | "push" | "blackjack", or None until settled.
    game_over   -- True once the hand is settled.
    """

    deck: Tuple[Card, ...]
    player_hand: Tuple[Card, ...]
    dealer_hand: Tuple[Card, ...]
    phase: str
    result: Optional[str]
    game_over: bool


# ---------------------------------------------------------------------------
# Pure hand evaluation
# ---------------------------------------------------------------------------

def hand_value(hand: Tuple[Card, ...]) -> int:
    """Return the best Blackjack total for *hand*.

    Every Ace counts as 11 first, then each Ace is downgraded to 1 (subtract 10)
    while the total would bust, giving the highest total <= 21 when possible
    (soft) and otherwise the minimal hard total.
    """
    total = sum(card_value(card) for card in hand)
    aces = sum(1 for card in hand if card[0] == 1)
    while total > BLACKJACK_VALUE and aces > 0:
        total -= 10   # demote one Ace from 11 to 1
        aces -= 1
    return total


def is_blackjack(hand: Tuple[Card, ...]) -> bool:
    """Return True if *hand* is a natural 21: exactly two cards totaling 21.

    The two-card guard is what makes a natural outrank a 21 built from 3+ cards.
    """
    return len(hand) == 2 and hand_value(hand) == BLACKJACK_VALUE


def is_bust(hand: Tuple[Card, ...]) -> bool:
    """Return True if *hand* exceeds 21."""
    return hand_value(hand) > BLACKJACK_VALUE


# ---------------------------------------------------------------------------
# Result resolution
# ---------------------------------------------------------------------------

def resolve_result(player_hand: Tuple[Card, ...], dealer_hand: Tuple[Card, ...]) -> str:
    """Compare two settled hands and return the player-relative result.

    Branch order matters. Naturals are checked first so a blackjack outranks an
    ordinary 21; then busts; then a plain total comparison.
    """
    player_bj = is_blackjack(player_hand)
    dealer_bj = is_blackjack(dealer_hand)

    # Naturals settle before anything else.
    if player_bj or dealer_bj:
        if player_bj and dealer_bj:
            return RESULT_PUSH
        return RESULT_BLACKJACK if player_bj else RESULT_LOSE

    # A player bust always loses; the dealer never needs to draw.
    if is_bust(player_hand):
        return RESULT_LOSE
    if is_bust(dealer_hand):
        return RESULT_WIN

    player_total = hand_value(player_hand)
    dealer_total = hand_value(dealer_hand)
    if player_total > dealer_total:
        return RESULT_WIN
    if player_total < dealer_total:
        return RESULT_LOSE
    return RESULT_PUSH


# ---------------------------------------------------------------------------
# Dealer auto-play
# ---------------------------------------------------------------------------

def _dealer_play(
    deck: Tuple[Card, ...], dealer_hand: Tuple[Card, ...]
) -> Tuple[Tuple[Card, ...], Tuple[Card, ...]]:
    """Draw for the dealer until the hand value reaches DEALER_STAND_MIN.

    The dealer stands on any 17 or higher, including a soft 17, because
    :func:`hand_value` already returns the best (soft) total. Returns the new
    ``(deck, dealer_hand)`` pair without mutating the inputs.
    """
    while hand_value(dealer_hand) < DEALER_STAND_MIN:
        dealer_hand = dealer_hand + (deck[0],)
        deck = deck[1:]
    return deck, dealer_hand


# ---------------------------------------------------------------------------
# Game lifecycle and transitions
# ---------------------------------------------------------------------------

def new_game(rng: random.Random) -> GameState:
    """Deal a fresh hand from a shuffled deck.

    Two cards go to the player and two to the dealer. If either side holds a
    natural, the hand is settled immediately (phase "result"); otherwise the
    player acts (phase "player").
    """
    deck_list = list(full_deck())
    rng.shuffle(deck_list)
    deck = tuple(deck_list)

    player_hand = (deck[0], deck[2])
    dealer_hand = (deck[1], deck[3])
    deck = deck[4:]

    state = GameState(
        deck=deck,
        player_hand=player_hand,
        dealer_hand=dealer_hand,
        phase=PHASE_PLAYER,
        result=None,
        game_over=False,
    )

    # Resolve naturals at the deal; do not auto-settle an ordinary hand.
    if is_blackjack(player_hand) or is_blackjack(dealer_hand):
        result = resolve_result(player_hand, dealer_hand)
        return replace(state, phase=PHASE_RESULT, result=result, game_over=True)
    return state


def hit(state: GameState) -> GameState:
    """Draw one card for the player.

    A bust settles the hand immediately as a loss; the dealer never draws.
    """
    if state.game_over or state.phase != PHASE_PLAYER:
        return state

    player_hand = state.player_hand + (state.deck[0],)
    deck = state.deck[1:]

    if is_bust(player_hand):
        return replace(
            state,
            deck=deck,
            player_hand=player_hand,
            phase=PHASE_RESULT,
            result=RESULT_LOSE,
            game_over=True,
        )
    return replace(state, deck=deck, player_hand=player_hand)


def stand(state: GameState) -> GameState:
    """End the player's turn and let the dealer play to completion.

    The dealer draws to at least 17, then the hand is compared and settled.
    """
    if state.game_over or state.phase != PHASE_PLAYER:
        return state

    deck, dealer_hand = _dealer_play(state.deck, state.dealer_hand)
    result = resolve_result(state.player_hand, dealer_hand)
    return replace(
        state,
        deck=deck,
        dealer_hand=dealer_hand,
        phase=PHASE_RESULT,
        result=result,
        game_over=True,
    )

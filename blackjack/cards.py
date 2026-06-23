"""Shared card primitives for Blackjack.

A card is a plain ``(rank, suit)`` tuple so a hand or deck is a fully immutable
value. ``rank`` is 1..13 (1=Ace, 11=Jack, 12=Queen, 13=King) and ``suit`` is
0..3. This module is pure: it never imports ``blessed`` and is shared by both
``game.py`` (rank -> point value) and ``render.py`` (rank/suit -> glyphs).
"""
from __future__ import annotations

from typing import Tuple

# A single playing card: (rank, suit). rank 1..13, suit 0..3.
Card = Tuple[int, int]

RANKS = tuple(range(1, 14))   # 1..13
SUITS = tuple(range(0, 4))    # 0..3

# Display glyphs. Ranks use the short labels seen on real cards; suits use the
# standard Unicode card-suit symbols (ASCII-safe, not CJK).
RANK_LABELS = {
    1: "A",
    2: "2", 3: "3", 4: "4", 5: "5", 6: "6",
    7: "7", 8: "8", 9: "9", 10: "10",
    11: "J", 12: "Q", 13: "K",
}
SUIT_GLYPHS = ("♠", "♥", "♦", "♣")  # spade, heart, diamond, club


def card_value(card: Card) -> int:
    """Return the Blackjack point value of *card*, counting every Ace as 11.

    Faces (J/Q/K) are worth 10; numbers are worth their rank. Aces return 11
    here; the soft/hard downgrade is handled by :func:`game.hand_value`.
    """
    rank = card[0]
    if rank == 1:
        return 11
    if rank >= 10:   # 10, J(11), Q(12), K(13) all score 10
        return 10
    return rank


def full_deck() -> Tuple[Card, ...]:
    """Return the ordered 52-card deck as a tuple of ``(rank, suit)``."""
    return tuple((rank, suit) for suit in SUITS for rank in RANKS)


def rank_label(card: Card) -> str:
    """Return the short rank label for *card* (e.g. ``"A"``, ``"10"``, ``"K"``)."""
    return RANK_LABELS[card[0]]


def suit_glyph(card: Card) -> str:
    """Return the suit symbol for *card*."""
    return SUIT_GLYPHS[card[1]]

"""Render a :class:`game.GameState` to the terminal using blessed.

The whole frame is composed as one string and printed after moving the cursor
home, so there is no full-screen clear between frames and therefore no flicker.
Every line is padded to a fixed width so a shorter line never leaves stale
characters behind from the previous frame.
"""
from __future__ import annotations

from typing import List, Optional

from blessed import Terminal

import cards as C
import game as G

# Layout constants.
ORIGIN_X = 3
ORIGIN_Y = 1
PANEL_GAP = 4
PANEL_WIDTH = 22

# A rendered card is 5 columns wide and 4 rows tall, including its border.
CARD_WIDTH = 5
CARD_HEIGHT = 4
CARD_SEP = 1
# A face-down card hides its rank/suit behind a hatched back.
_BACK_FILL = "▚▚▚"

# The card area uses a FIXED width so the side panel never shifts as a hand
# grows. A wider hand simply fills more of this reserved space; padding every
# line to CONTENT_WIDTH then overwrites any stale characters from the previous
# (possibly narrower) frame. LAYOUT_CARDS is a generous upper bound on the
# cards a single hand can reach without busting.
LAYOUT_CARDS = 11

# Truecolor per suit (red suits vs black suits) and the card back.
_RED_RGB = (200, 60, 60)
_BLACK_RGB = (40, 40, 50)
_BACK_RGB = (70, 90, 150)


def _pad(term: Terminal, text: str, width: int) -> str:
    """Right-pad *text* to a fixed printable width, ignoring escape codes."""
    extra = width - term.length(text)
    return text + " " * extra if extra > 0 else text


def _suit_rgb(card: C.Card) -> tuple:
    """Return the truecolor RGB used to draw *card* (hearts/diamonds are red)."""
    return _RED_RGB if card[1] in (1, 2) else _BLACK_RGB


def card_lines(term: Terminal, card: C.Card, face_up: bool) -> List[str]:
    """Return the CARD_HEIGHT strings that draw one card.

    A real *card* is always supplied; when *face_up* is False its rank and suit
    are hidden behind a hatched back (the card itself is then unused).
    """
    if not face_up:
        color = term.color_rgb(*_BACK_RGB)
        return [
            "┌───┐",
            "│" + color(_BACK_FILL) + "│",
            "│" + color(_BACK_FILL) + "│",
            "└───┘",
        ]

    label = C.rank_label(card)            # "A", "2".."10", "J", "Q", "K"
    glyph = C.suit_glyph(card)
    color = term.color_rgb(*_suit_rgb(card))
    # Rank sits top-left (left-justified in the 3 inner columns); suit is
    # centred on the row below. "10" fills both of its two columns; the rest
    # are single characters padded on the right.
    rank_row = label.ljust(3)
    return [
        "┌───┐",
        "│" + color(rank_row) + "│",
        "│ " + color(glyph) + " │",
        "└───┘",
    ]


def hand_lines(term: Terminal, hand: tuple, hide_hole: bool) -> List[str]:
    """Lay out every card in *hand* side by side as CARD_HEIGHT strings.

    When *hide_hole* is True the second card is drawn face-down (the dealer's
    hidden hole card during the player's turn).
    """
    rendered = []
    for i, card in enumerate(hand):
        face_up = not (hide_hole and i == 1)
        rendered.append(card_lines(term, card, face_up))

    lines: List[str] = []
    sep = " " * CARD_SEP
    for row in range(CARD_HEIGHT):
        lines.append(sep.join(card[row] for card in rendered))
    return lines


def _hand_width(card_count: int) -> int:
    """Pixel width of a row of *card_count* cards including separators."""
    if card_count <= 0:
        return CARD_WIDTH
    return card_count * CARD_WIDTH + (card_count - 1) * CARD_SEP


# Fixed width reserved for the card area; the panel is positioned from this so
# it never moves as a hand grows.
CONTENT_WIDTH = _hand_width(LAYOUT_CARDS)


def dealer_total_text(term: Terminal, state: G.GameState) -> str:
    """Return the dealer's total label, hiding it during the player's turn."""
    if state.phase == G.PHASE_PLAYER:
        # Only the up-card is known to the player.
        up_value = G.hand_value((state.dealer_hand[0],))
        return f"Dealer  {up_value} + ?"
    return f"Dealer  {G.hand_value(state.dealer_hand)}"


def panel_lines(term: Terminal, state: G.GameState) -> List[str]:
    """Return the right-side info panel as a list of strings."""
    lines = [
        term.bold("BLACKJACK"),
        "",
        dealer_total_text(term, state),
        f"Player  {G.hand_value(state.player_hand)}",
        "",
        term.dim("h       히트"),
        term.dim("s       스탠드"),
        term.dim("r       새 판"),
        term.dim("q       종료"),
    ]
    return lines


def _banner(term: Terminal, result: Optional[str]) -> str:
    """Return the styled result banner for a settled hand."""
    if result == G.RESULT_BLACKJACK:
        return term.bold(term.green(" BLACKJACK! "))
    if result == G.RESULT_WIN:
        return term.bold(term.green(" WIN "))
    if result == G.RESULT_LOSE:
        return term.bold(term.red(" LOSE "))
    return term.bold(term.yellow(" PUSH "))


def draw(term: Terminal, state: G.GameState) -> None:
    """Compose and print the full frame without clearing the screen."""
    frame: List[str] = [term.home]

    # During the player's turn the dealer's hole card stays hidden.
    hide_hole = state.phase == G.PHASE_PLAYER
    dealer_render = hand_lines(term, state.dealer_hand, hide_hole)
    player_render = hand_lines(term, state.player_hand, False)

    # The card area is a fixed width so the panel never shifts between frames.
    y = ORIGIN_Y
    frame.append(term.move_xy(ORIGIN_X, y) + _pad(term, term.dim("DEALER"), CONTENT_WIDTH))
    y += 1
    for line in dealer_render:
        frame.append(term.move_xy(ORIGIN_X, y) + _pad(term, line, CONTENT_WIDTH))
        y += 1

    y += 1
    frame.append(term.move_xy(ORIGIN_X, y) + _pad(term, term.dim("PLAYER"), CONTENT_WIDTH))
    y += 1
    for line in player_render:
        frame.append(term.move_xy(ORIGIN_X, y) + _pad(term, line, CONTENT_WIDTH))
        y += 1

    # Result banner under the hands.
    y += 1
    banner = _banner(term, state.result) if state.game_over else ""
    frame.append(term.move_xy(ORIGIN_X, y) + _pad(term, banner, CONTENT_WIDTH))

    # Side panel, positioned from the fixed content width.
    panel_x = ORIGIN_X + CONTENT_WIDTH + PANEL_GAP
    for i, line in enumerate(panel_lines(term, state)):
        frame.append(term.move_xy(panel_x, ORIGIN_Y + i) + _pad(term, line, PANEL_WIDTH))

    print("".join(frame), end="", flush=True)

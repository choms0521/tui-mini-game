# Project conventions — tui-mini-game

A collection of single-screen terminal games (Python + `blessed`). Every game lives
in its own folder and follows the same structure. **These rules apply to every
existing game and to every game added in the future.**

## Game folder structure

| File | Role |
| --- | --- |
| `game.py` | Immutable state (`@dataclass(frozen=True)`) + pure transitions. No `blessed` import. |
| `board.py` / `config.py` / `levels.py` / `cards.py` / `solver.py` | Optional helpers (grid constants, data, search). |
| `render.py` | `blessed` truecolor rendering. Flicker-free: compose one frame, print after `term.home`, pad every line to a fixed width with `term.length`. |
| `main.py` | `blessed` input loop (entry point). |
| `selftest.py` | Headless self-test; `python selftest.py` exits 0 on pass. |
| `meta.json` | Launcher metadata: `{"name", "description", "entry": "main.py"}`. |
| `run.sh` | Executable launch wrapper (copy an existing game's `run.sh`). |

Core principles: immutable state (use `dataclasses.replace`, never mutate); inject a
`random.Random` for any randomness so tests stay deterministic; keep `game.py` free of
`blessed`; the launcher auto-discovers games via `meta.json` (no launcher edits needed).

## In-game how-to (REQUIRED for every game)

Players must be able to learn each game from inside it. Every game's side panel and
input loop MUST provide a Korean how-to:

1. **Panel summary** — `render.py:panel_lines` includes a short Korean how-to (goal +
   how to play) right under the title, wrapped so every panel line satisfies
   `term.length(line) <= PANEL_WIDTH`. Keep it ~4–6 lines (3 for already-tall panels).
2. **Help overlay** — `render.py` defines `HELP_LINES` (detailed Korean) and a
   `help_overlay(term, ...)` that draws them as a centered block; `draw(...)` takes a
   `show_help: bool = False` arg and renders the overlay first when true.
3. **Toggle key** — `main.py` maps `h` and `?` to toggle `show_help` (pausing real-time
   games while shown), passes it to `draw`, and resets it on restart. A control hint
   `term.dim("h       도움말")` appears in the panel. Exception: if `h` is already a
   gameplay key (e.g. Blackjack hit, Wordle letter), use `?` only and show `?  도움말`.

## Language

- Player-facing strings (panel summary, help, banners): **Korean**.
- All code identifiers, comments, and docstrings: standard technical English.
- **No Chinese characters (한자) anywhere.** Korean Hangul + ASCII only.

## Layout budget

- Total frame width `BOARD_X + board_width + PANEL_GAP + PANEL_WIDTH` must stay `<= 80`
  (Pong and Tron are pre-existing exceptions whose boards are inherently wider).
  Only widen `PANEL_WIDTH` if the frame stays within budget; otherwise wrap to more,
  shorter lines.
- Target terminal: **80×30** minimum. Document any game that needs more.
- Verify with the layout harness — it gates panel overflow, frame width, and the
  presence of the Korean how-to:

  ```bash
  .venv/bin/python tools/layout_harness.py            # all games
  .venv/bin/python tools/layout_harness.py <game>     # one game
  ```

- `selftest.py` SHOULD assert the panel carries the how-to (panel contains the summary,
  every panel line `<= PANEL_WIDTH`, and `draw(show_help=True)` composes without error).

## When you add a game

1. Create the game folder with all files above, including the in-game how-to.
2. Make `tools/layout_harness.py <game>` and `python <game>/selftest.py` pass.
3. Add a row to `README.md`'s game table and a section to `docs/PLAY-ko.md`.
4. No `__pycache__` or debug code in commits.

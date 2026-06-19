# Terminal Tetris

A Tetris clone that runs entirely in your terminal, built with Python and
[`blessed`](https://blessed.readthedocs.io/). It has 7-bag piece randomization,
wall-kick rotation, a ghost (landing) preview, hard drop, scoring, and a level
curve that speeds up as you clear lines.

## Requirements

- Python 3.10+
- A terminal with truecolor support (macOS Terminal, iTerm2, most modern
  terminals). At least an 80x24 window is recommended.
- The shared virtual environment at the workspace root (`../.venv`). Recreate it
  from the workspace root if needed:

  ```bash
  python3 -m venv .venv
  .venv/bin/pip install -r requirements.txt
  ```

## Play

```bash
./run.sh
```

or, manually, from this folder:

```bash
../.venv/bin/python main.py
```

## Controls

| Key            | Action          |
| -------------- | --------------- |
| Left / Right   | Move piece      |
| Up / `x`       | Rotate clockwise|
| `z`            | Rotate counter-clockwise |
| Down           | Soft drop       |
| Space          | Hard drop       |
| `p`            | Pause / resume  |
| `r`            | Restart (after game over) |
| `q`            | Quit            |

## Scoring

Points scale with the level: 1 line = 100, 2 = 300, 3 = 500, 4 (a Tetris) = 800,
all multiplied by the current level. Hard drops add 2 points per cell dropped.
The level rises by one for every 10 lines cleared, shortening the gravity step.

## Project layout

| File           | Responsibility                                   |
| -------------- | ------------------------------------------------ |
| `pieces.py`    | Tetromino shapes, rotation, 7-bag randomizer     |
| `board.py`     | Grid, collision detection, locking, line clears  |
| `game.py`      | Immutable game state and all transitions         |
| `render.py`    | Drawing the board and side panel with blessed     |
| `main.py`      | Terminal setup, input handling, the game loop    |
| `selftest.py`  | Headless logic tests (no TTY needed)             |

## Tests

```bash
../.venv/bin/python selftest.py
```

# Terminal Breakout

A Breakout / brick-breaker clone that runs in the terminal, built with Python
and [`blessed`](https://blessed.readthedocs.io/). Bounce the ball off the paddle
to clear every brick; the field refills and speeds up each level.

## Requirements

- Python 3.10+
- A terminal with truecolor support, at least ~62x28.
- The shared virtual environment at the workspace root (`../.venv`). Recreate it
  from the workspace root with:

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

| Key          | Action            |
| ------------ | ----------------- |
| Left / Right | Move the paddle (also `a` / `d`) |
| Space        | Launch the ball   |
| `p`          | Pause / resume    |
| `r`          | Restart           |
| `q`          | Quit              |

## Rules

- The ball reflects off walls, the ceiling, and the paddle. Where it lands on
  the paddle nudges its horizontal direction, so you can aim.
- Each brick is worth 10 points. Clear the whole field to advance a level; every
  level refills the bricks and makes the ball a little faster.
- Miss the ball and you lose a life. The game ends at zero lives — press `r`
  to start again.

## Project layout

| File          | Responsibility                                |
| ------------- | --------------------------------------------- |
| `config.py`   | Playfield, paddle, brick, and timing constants |
| `game.py`     | Immutable game state, ball physics, collisions |
| `render.py`   | Drawing the board and side panel with blessed  |
| `main.py`     | Terminal setup, input handling, the game loop  |
| `selftest.py` | Headless logic tests (no TTY needed)           |

## Tests

```bash
../.venv/bin/python selftest.py
```

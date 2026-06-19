# mini-game

A small collection of terminal games written in Python with
[`blessed`](https://blessed.readthedocs.io/). Every game shares one virtual
environment at the workspace root and follows the same design: an immutable game
state, flicker-free truecolor rendering, and headless self-tests.

## Games

| Game                  | Folder      | Description                                  |
| --------------------- | ----------- | -------------------------------------------- |
| [Tetris](./tetris)    | `tetris/`   | 7-bag pieces, wall kicks, ghost, hard drop   |
| [Breakout](./breakout)| `breakout/` | Brick breaker with paddle aim and levels     |

## Setup

Create the shared virtual environment once, from this directory:

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
```

## Play

Each game has its own launcher that uses the shared `.venv`:

```bash
./tetris/run.sh
./breakout/run.sh
```

## Tests

```bash
.venv/bin/python tetris/selftest.py
.venv/bin/python breakout/selftest.py
```

## Requirements

- Python 3.10+
- A terminal with truecolor support (macOS Terminal, iTerm2, most modern terminals)

## Layout

```
mini-game/
├── .venv/            # shared virtual environment (git-ignored)
├── requirements.txt  # shared dependencies (blessed)
├── tetris/
└── breakout/
```

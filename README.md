# mini-game

A small collection of terminal games written in Python with
[`blessed`](https://blessed.readthedocs.io/). Every game shares one virtual
environment at the workspace root and follows the same design: an immutable game
state, flicker-free truecolor rendering, and headless self-tests.

> 한국어 플레이 안내는 [`docs/PLAY-ko.md`](./docs/PLAY-ko.md)를 참고하세요. 게임을
> 실행하면 화면 옆 패널에 게임 설명과 조작법이 한국어로 표시되고, `h`(또는 `?`) 키를
> 누르면 자세한 도움말이 화면 중앙에 나타납니다.

## Games

| Game                              | Folder            | Description                                  |
| --------------------------------- | ----------------- | -------------------------------------------- |
| [Tetris](./tetris)                | `tetris/`         | 7-bag pieces, wall kicks, ghost, hard drop   |
| [Breakout](./breakout)            | `breakout/`       | Brick breaker with paddle aim and levels     |
| [Snake](./snake)                  | `snake/`          | Grow by eating, avoid the walls and yourself |
| [2048](./2048)                    | `2048/`           | Slide and merge tiles to reach 2048          |
| [Minesweeper](./minesweeper)      | `minesweeper/`    | Clear the field without hitting a mine       |
| [Space Invaders](./space_invaders)| `space_invaders/` | Shoot the descending alien fleet             |
| [Roguelike](./roguelike)          | `roguelike/`      | Explore the dungeon, fight monsters, descend |
| [Wordle](./wordle)                | `wordle/`         | Guess the hidden 5-letter word in six tries  |
| [Sokoban](./sokoban)              | `sokoban/`        | Push every box onto a goal                   |
| [Pong](./pong)                    | `pong/`           | Paddle duel against a simple AI              |
| [Connect Four](./connect_four)    | `connect_four/`   | Drop discs and connect four against the AI   |
| [Mastermind](./mastermind)        | `mastermind/`     | Crack the hidden color code from hint pegs   |
| [Sudoku](./sudoku)                | `sudoku/`         | Fill the 9x9 grid with 1-9, no repeats       |
| [Reversi](./reversi)              | `reversi/`        | Outflank and flip discs against the AI       |
| [Gomoku](./gomoku)                | `gomoku/`         | Line up five in a row against the AI         |
| [Battleship](./battleship)        | `battleship/`     | Hunt and sink the hidden enemy fleet (AI)    |
| [Blackjack](./blackjack)          | `blackjack/`      | Beat the dealer to 21 without going bust     |
| [Tron](./tron)                    | `tron/`           | Trap the AI behind your light-cycle trail    |
| [Frogger](./frogger)              | `frogger/`        | Cross the road and river to the goal slots   |

## Setup

Create the shared virtual environment once, from this directory:

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
```

## Play

The easiest way is the launcher — a menu that lists every game and runs the one
you pick as a separate process, returning to the menu when you quit it:

```bash
./play.sh
```

Use up/down to select, enter to play, and `q` to quit (the menu, or a game back
to the menu). You can still launch a single game directly:

```bash
./tetris/run.sh
./breakout/run.sh
```

### Adding a game to the launcher

Drop a folder next to the others with a runnable `main.py` and an optional
`meta.json`; the launcher discovers it automatically on the next run:

```json
{ "name": "Snake", "description": "classic snake", "entry": "main.py" }
```

A folder with no `meta.json` still appears (named after the folder); a folder
with no runnable entry is skipped.

## Tests

```bash
.venv/bin/python launcher/selftest.py
.venv/bin/python tetris/selftest.py
.venv/bin/python breakout/selftest.py
```

## Requirements

- Python 3.10+
- A terminal with truecolor support (macOS Terminal, iTerm2, most modern terminals)
- A terminal at least **80×30**; a few wide games need more (Tron ~112 columns, Pong ~85).
  Each game prints a size hint if the window is too small.

## Layout

```
mini-game/
├── .venv/            # shared virtual environment (git-ignored)
├── requirements.txt  # shared dependencies (blessed)
├── play.sh           # launcher menu (runs each game as a child process)
├── launcher/         # menu: discovery + render + selftest
├── docs/             # PLAY-ko.md (Korean guide), game candidates, plans
├── tetris/           # each game folder: main.py + meta.json + selftest.py
├── breakout/
├── snake/
├── 2048/
├── minesweeper/
├── space_invaders/
├── roguelike/
├── wordle/
├── sokoban/
├── pong/
├── connect_four/
├── mastermind/
├── sudoku/
├── reversi/
├── gomoku/
├── battleship/
├── blackjack/
├── tron/
└── frogger/
```

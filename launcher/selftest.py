"""Headless checks for the launcher (no terminal required).

Run with ``python selftest.py``. Exercises game discovery (meta.json parsing,
fallbacks, skipping non-games, surviving a broken meta.json) and the menu string
builder, mirroring the self-test style of the bundled games so the launcher can
be verified in CI or over SSH where no interactive TTY is available.
"""
from __future__ import annotations

import io
import json
import tempfile
from contextlib import redirect_stdout
from pathlib import Path

from blessed import Terminal

import discover as D
import render as R


def check(condition: bool, label: str) -> None:
    if not condition:
        raise AssertionError(f"FAILED: {label}")
    print(f"ok - {label}")


def _make_game(folder: Path, entry: str = "main.py", meta: dict | None = None) -> None:
    folder.mkdir(parents=True, exist_ok=True)
    if entry is not None:
        (folder / entry).write_text("print('hi')\n", encoding="utf-8")
    if meta is not None:
        (folder / "meta.json").write_text(json.dumps(meta), encoding="utf-8")


def test_discovery_with_meta() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        _make_game(root / "tetris", meta={"name": "Tetris", "description": "blocks"})
        games = D.discover_games(root)
        check(len(games) == 1, "one game discovered from a folder with meta.json")
        check(games[0].name == "Tetris", "meta.json name is used")
        check(games[0].description == "blocks", "meta.json description is used")
        check(games[0].entry.name == "main.py", "entry resolves to the script")


def test_discovery_fallback_without_meta() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        _make_game(root / "snake", meta=None)  # main.py present, no meta.json
        games = D.discover_games(root)
        check(len(games) == 1, "a folder with main.py but no meta.json still registers")
        check(games[0].name.lower() == "snake", "folder name is the fallback name")


def test_skips_non_games() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        (root / "docs").mkdir()                 # no runnable entry
        (root / ".venv").mkdir()                # hidden, ignored
        launcher = root / "launcher"            # the launcher itself, ignored
        launcher.mkdir()
        (launcher / "main.py").write_text("x\n", encoding="utf-8")
        _make_game(root / "tetris", meta={"name": "Tetris"})
        names = [g.name for g in D.discover_games(root)]
        check(names == ["Tetris"], "only real game folders are discovered")


def test_broken_meta_does_not_crash() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        _make_game(root / "broken", meta=None)
        (root / "broken" / "meta.json").write_text("{ not valid json", encoding="utf-8")
        games = D.discover_games(root)
        check(len(games) == 1, "a broken meta.json falls back instead of crashing")
        check(games[0].name.lower() == "broken", "fallback name used when meta.json is invalid")


def test_menu_renders() -> None:
    term = Terminal(force_styling=True)
    games = (
        D.Game(name="Tetris", description="blocks", entry=Path("/x/main.py")),
        D.Game(name="Breakout", description="bricks", entry=Path("/y/main.py")),
    )
    lines = R.menu_lines(term, games, selected=0)
    check(any("Tetris" in line for line in lines), "menu lists the first game")
    check(any("Breakout" in line for line in lines), "menu lists the second game")

    with redirect_stdout(io.StringIO()):
        R.draw(term, games, 0)
        R.draw(term, games, 1)
        R.draw(term, games, 0, message="something broke")
    check(True, "draw() composes menu frames without error")


def test_empty_menu_renders() -> None:
    term = Terminal(force_styling=True)
    lines = R.menu_lines(term, (), selected=0)
    check(any("no games" in line.lower() for line in lines), "empty menu shows a hint")


def main() -> None:
    tests = [
        test_discovery_with_meta,
        test_discovery_fallback_without_meta,
        test_skips_non_games,
        test_broken_meta_does_not_crash,
        test_menu_renders,
        test_empty_menu_renders,
    ]
    for test in tests:
        test()
    print(f"\nAll {len(tests)} test groups passed.")


if __name__ == "__main__":
    main()

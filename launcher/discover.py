"""Discover playable games by scanning sibling folders for a ``meta.json``.

Each game folder may carry a ``meta.json`` describing how the launcher should
present and run it. Folders without one fall back to sensible defaults so a
game can still be launched, and folders with no runnable entry are skipped.
Discovery never raises on a single bad folder: a broken ``meta.json`` degrades
to the fallback rather than crashing the whole menu.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Tuple

# Folders next to the launcher that are never games.
_IGNORED = {"launcher", "__pycache__"}


@dataclass(frozen=True)
class Game:
    """A launchable game: how to show it and which script to run."""

    name: str
    description: str
    entry: Path  # absolute path to the script the launcher executes


def _load_meta(folder: Path) -> dict:
    """Read ``meta.json`` if present; return an empty dict on any problem."""
    meta_path = folder / "meta.json"
    if not meta_path.is_file():
        return {}
    try:
        with meta_path.open(encoding="utf-8") as handle:
            data = json.load(handle)
    except (json.JSONDecodeError, OSError):
        # A broken meta.json should never take down the launcher; fall back.
        return {}
    return data if isinstance(data, dict) else {}


def _game_from_folder(folder: Path) -> Optional[Game]:
    """Build a :class:`Game` for one folder, or ``None`` if nothing runnable."""
    meta = _load_meta(folder)
    entry = folder / meta.get("entry", "main.py")
    if not entry.is_file():
        return None  # no runnable script here; skip quietly
    name = meta.get("name") or folder.name.capitalize()
    description = meta.get("description", "")
    return Game(name=name, description=description, entry=entry.resolve())


def discover_games(root: Path) -> Tuple[Game, ...]:
    """Return every runnable game found directly under ``root``, sorted by name."""
    folders = sorted(
        path
        for path in root.iterdir()
        if path.is_dir()
        and not path.name.startswith(".")
        and path.name not in _IGNORED
    )
    games = tuple(
        game
        for folder in folders
        if (game := _game_from_folder(folder)) is not None
    )
    return games

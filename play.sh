#!/usr/bin/env bash
# Launch the mini-game menu using the shared workspace virtual environment.
set -euo pipefail
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
exec "$DIR/.venv/bin/python" "$DIR/launcher/main.py"

#!/usr/bin/env bash
# Launch Sokoban using the shared workspace virtual environment, from any dir.
set -euo pipefail
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
exec "$DIR/../.venv/bin/python" "$DIR/main.py"

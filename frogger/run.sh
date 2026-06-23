#!/usr/bin/env bash
# Launch Frogger using the shared workspace virtual environment, from any dir.
set -euo pipefail
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
exec "$DIR/../.venv/bin/python" "$DIR/main.py"

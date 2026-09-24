#!/usr/bin/env bash
#
# Project Manager - start the server from the virtual environment.
#
set -e

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_DIR"

if [ -x "$PROJECT_DIR/../.venv/bin/python" ]; then
    PYTHON="$PROJECT_DIR/../.venv/bin/python"
elif [ -x "$PROJECT_DIR/.venv/bin/python" ]; then
    PYTHON="$PROJECT_DIR/.venv/bin/python"
else
    PYTHON="python3"
fi

echo "Starting Project Manager at http://127.0.0.1:8000"
echo "To stop: press Ctrl+C"
echo

"$PYTHON" server.py

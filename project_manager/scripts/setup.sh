#!/usr/bin/env bash
#
# Project Manager - one-time setup for (Chromebook) Linux.
# Creates a virtual environment and installs dependencies.
#
set -e

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_DIR"

if ! command -v python3 >/dev/null 2>&1; then
    echo "error: python3 was not found." >&2
    echo "On ChromeOS, enable Linux and then run:" >&2
    echo "  sudo apt update" >&2
    echo "  sudo apt install -y python3 python3-venv python3-pip" >&2
    exit 1
fi

if [ ! -d ".venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv .venv
else
    echo "Virtual environment already exists."
fi

echo "Installing dependencies..."
.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install -r requirements.txt

echo
echo "Setup complete. Start the server with:  ./run.sh"
echo "Then open:  http://127.0.0.1:8000"

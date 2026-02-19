#!/usr/bin/env bash
set -euo pipefail

python3 -m pip install --upgrade pip
python3 -m pip install pyinstaller==6.10.0
pyinstaller --clean planner.spec

echo "Done: dist/tire-planner"

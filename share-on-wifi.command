#!/bin/bash
# Double-click to serve the player to your phone / iPad on the same wifi.
# This exposes THIS FOLDER, read-only, to your local network while it runs.
# Close the window (or Ctrl-C) to stop.
cd "$(dirname "$0")" || exit 1
PORT=8800
while lsof -i :$PORT -sTCP:LISTEN -t >/dev/null 2>&1; do PORT=$((PORT+1)); done
python3 serve.py "$PORT" --lan

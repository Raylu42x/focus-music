#!/bin/bash
# Double-click this to start the focus player.
# Serves this folder on localhost only and opens the page.
cd "$(dirname "$0")" || exit 1
PORT=8800
while lsof -i :$PORT -sTCP:LISTEN -t >/dev/null 2>&1; do PORT=$((PORT+1)); done
echo "Serving $(pwd) on http://127.0.0.1:$PORT"
echo "Close this window (or press Ctrl-C) to stop."
python3 serve.py "$PORT" >/dev/null 2>&1 &
SRV=$!
trap 'kill $SRV 2>/dev/null' EXIT INT TERM
sleep 1
open "http://127.0.0.1:$PORT/index.html"
wait $SRV

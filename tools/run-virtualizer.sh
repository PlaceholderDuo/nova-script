#!/bin/bash
# Launch the Novation Hardware Virtualizer
# Opens the virtual MIDI bridge server + the visual web UI
# MIDI ports auto-connect on startup — nova-script can connect immediately

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
HTML_FILE="$SCRIPT_DIR/novation-virtualizer.html"
PYTHON="$SCRIPT_DIR/../.venv/bin/python"

if [ ! -f "$PYTHON" ]; then
    echo "Error: venv not found at $PYTHON"
    echo "Run: python3 -m venv .venv && .venv/bin/pip install -e '.[tools]'"
    exit 1
fi

echo "=== Novation Virtualizer ==="
echo ""

"$PYTHON" "$SCRIPT_DIR/novation-virtualizer.py" &
PID=$!
sleep 2

if kill -0 $PID 2>/dev/null; then
    echo "Backend running (PID $PID)"
    echo "Virtual MIDI ports created — nova-script can connect now"
    echo "Opening visualizer in browser..."
    open "$HTML_FILE"
    echo ""
    echo "Press Ctrl+C to stop"
    wait $PID
else
    echo "ERROR: Backend failed to start"
    exit 1
fi

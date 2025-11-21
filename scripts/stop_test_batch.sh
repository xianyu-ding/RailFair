#!/bin/bash
# Stop background batch collection process
# Usage: ./stop_test_batch.sh [pid_file]

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

LOG_DIR="logs"

# If PID file provided, use it; otherwise find latest
if [ -n "$1" ]; then
    PID_FILE="$1"
else
    # Find latest PID file
    PID_FILE=$(ls -t "$LOG_DIR"/test_batch_*.pid 2>/dev/null | head -1)
fi

if [ -z "$PID_FILE" ] || [ ! -f "$PID_FILE" ]; then
    echo "❌ No PID file found. Process may not be running."
    exit 1
fi

PID=$(cat "$PID_FILE")

if ! ps -p "$PID" > /dev/null 2>&1; then
    echo "⚠️  Process $PID is not running (may have already finished)"
    rm -f "$PID_FILE"
    exit 0
fi

echo "🛑 Stopping process $PID..."
kill "$PID"

# Wait for process to stop
for i in {1..10}; do
    if ! ps -p "$PID" > /dev/null 2>&1; then
        echo "✅ Process stopped successfully"
        rm -f "$PID_FILE"
        exit 0
    fi
    sleep 1
done

# Force kill if still running
if ps -p "$PID" > /dev/null 2>&1; then
    echo "⚠️  Process still running, force killing..."
    kill -9 "$PID"
    sleep 1
    rm -f "$PID_FILE"
    echo "✅ Process force stopped"
fi


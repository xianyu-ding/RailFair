#!/bin/bash
# Stop Phase 3 background batch collection process
# Usage: ./stop_phase3.sh [pid_file]

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

LOG_DIR="logs"

# If PID file provided, use it; otherwise find latest
if [ -n "$1" ]; then
    PID_FILE="$1"
else
    PID_FILE=$(ls -t "$LOG_DIR"/phase3_batch_*.pid 2>/dev/null | head -1)
fi

if [ -z "$PID_FILE" ] || [ ! -f "$PID_FILE" ]; then
    echo "❌ No Phase 3 PID file found. Process may not be running."
    exit 1
fi

PID=$(cat "$PID_FILE")
TIMESTAMP=$(basename "$PID_FILE" .pid | sed 's/phase3_batch_//')
LOG_FILE="${LOG_DIR}/phase3_batch_${TIMESTAMP}.log"
STATUS_FILE="${LOG_DIR}/phase3_batch_${TIMESTAMP}.status"

if ! ps -p "$PID" > /dev/null 2>&1; then
    echo "⚠️  Process $PID is not running (may have already finished)"
    rm -f "$PID_FILE" "$STATUS_FILE"
    exit 0
fi

echo "🛑 Stopping Phase 3 process $PID..."
echo "   This may take a moment as current requests complete..."
echo ""

# Send SIGTERM first (graceful shutdown)
kill "$PID"

# Wait for process to stop gracefully
for i in {1..30}; do
    if ! ps -p "$PID" > /dev/null 2>&1; then
        echo "✅ Process stopped successfully"
        rm -f "$PID_FILE" "$STATUS_FILE"
        echo ""
        echo "📊 Final status saved in:"
        echo "   Log: $LOG_FILE"
        echo "   Progress: data/progress_phase3.json"
        exit 0
    fi
    sleep 1
    if [ $((i % 5)) -eq 0 ]; then
        echo "   Still waiting... ($i/30 seconds)"
    fi
done

# Force kill if still running
if ps -p "$PID" > /dev/null 2>&1; then
    echo ""
    echo "⚠️  Process still running after 30 seconds, force killing..."
    kill -9 "$PID"
    sleep 1
    rm -f "$PID_FILE" "$STATUS_FILE"
    echo "✅ Process force stopped"
    echo ""
    echo "⚠️  Note: Force kill may have interrupted data saving."
    echo "   Check progress file: data/progress_phase3.json"
fi



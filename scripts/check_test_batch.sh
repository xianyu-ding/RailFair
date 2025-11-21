#!/bin/bash
# Check status of background batch collection
# Usage: ./check_test_batch.sh [pid_file]

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
TIMESTAMP=$(basename "$PID_FILE" .pid | sed 's/test_batch_//')
LOG_FILE="${LOG_DIR}/test_batch_${TIMESTAMP}.log"

echo "📊 Batch Collection Status"
echo "=========================="
echo "PID: $PID"
echo "Log file: $LOG_FILE"
echo ""

if ps -p "$PID" > /dev/null 2>&1; then
    echo "✅ Process is RUNNING"
    echo ""
    echo "📈 Process info:"
    ps -p "$PID" -o pid,ppid,etime,cmd
    echo ""
    echo "📝 Last 20 lines of log:"
    echo "---"
    if [ -f "$LOG_FILE" ]; then
        tail -n 20 "$LOG_FILE"
    else
        echo "Log file not found yet"
    fi
else
    echo "❌ Process is NOT RUNNING"
    echo ""
    if [ -f "$LOG_FILE" ]; then
        echo "📝 Last 20 lines of log:"
        echo "---"
        tail -n 20 "$LOG_FILE"
    fi
    echo ""
    echo "💡 You may want to remove the PID file: rm $PID_FILE"
fi


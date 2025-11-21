#!/bin/bash
# Test script for batch HSP data collection (background mode)
# Usage: ./test_batch_background.sh [config_file]

set -e

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Configuration
CONFIG_FILE="${1:-configs/hsp_config_test.yaml}"
LOG_DIR="logs"
OUTPUT_DIR="data"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
LOG_FILE="${LOG_DIR}/test_batch_${TIMESTAMP}.log"
PID_FILE="${LOG_DIR}/test_batch_${TIMESTAMP}.pid"

# Create necessary directories
mkdir -p "$LOG_DIR" "$OUTPUT_DIR"

# Check if Python script exists
if [ ! -f "fetch_hsp_batch.py" ]; then
    echo "❌ Error: fetch_hsp_batch.py not found in current directory"
    exit 1
fi

# Check if config file exists
if [ ! -f "$CONFIG_FILE" ]; then
    echo "❌ Error: Config file not found: $CONFIG_FILE"
    exit 1
fi

# Check for environment variables
if [ -z "$HSP_EMAIL" ] && [ -z "$HSP_USERNAME" ]; then
    echo "⚠️  Warning: HSP_EMAIL or HSP_USERNAME not set"
    echo "   Make sure .env file exists or export environment variables"
fi

# Function to check if process is running
check_process() {
    if [ -f "$PID_FILE" ]; then
        PID=$(cat "$PID_FILE")
        if ps -p "$PID" > /dev/null 2>&1; then
            return 0
        else
            rm -f "$PID_FILE"
            return 1
        fi
    fi
    return 1
}

# Check if already running
if check_process; then
    echo "⚠️  Process already running (PID: $(cat "$PID_FILE"))"
    echo "   Log file: $LOG_FILE"
    exit 1
fi

# Start background process
echo "🚀 Starting batch collection in background..."
echo "   Config: $CONFIG_FILE"
echo "   Log file: $LOG_FILE"
echo "   PID file: $PID_FILE"
echo ""

# Run in background with nohup
nohup python3 fetch_hsp_batch.py "$CONFIG_FILE" --phase "TEST" > "$LOG_FILE" 2>&1 &
PID=$!

# Save PID
echo $PID > "$PID_FILE"

# Wait a moment to check if process started successfully
sleep 2

if ps -p "$PID" > /dev/null 2>&1; then
    echo "✅ Process started successfully!"
    echo "   PID: $PID"
    echo "   Log file: $LOG_FILE"
    echo "   PID file: $PID_FILE"
    echo ""
    echo "📋 Useful commands:"
    echo "   View logs: tail -f $LOG_FILE"
    echo "   Check status: ps -p $PID"
    echo "   Stop process: kill $PID"
    echo "   Or use: ./stop_test_batch.sh $PID_FILE"
else
    echo "❌ Process failed to start. Check log file: $LOG_FILE"
    rm -f "$PID_FILE"
    exit 1
fi


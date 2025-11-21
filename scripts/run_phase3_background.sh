#!/bin/bash
# Phase 3 Batch Collection - Background Mode
# Uses small date chunks (≤7 days) and 1-3 second intervals between requests (consistent with Phase 1/2)
# Date Range: 2025-03-01 to 2025-04-30 (61 days, ~9 chunks per route)
# Routes: 10 routes
# Total chunks: ~270 chunks (10 routes × 3 day types × 9 date chunks)

set -e

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Configuration
CONFIG_FILE="configs/hsp_config_phase3.yaml"
LOG_DIR="logs"
OUTPUT_DIR="data"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
LOG_FILE="${LOG_DIR}/phase3_batch_${TIMESTAMP}.log"
PID_FILE="${LOG_DIR}/phase3_batch_${TIMESTAMP}.pid"
STATUS_FILE="${LOG_DIR}/phase3_batch_${TIMESTAMP}.status"

# Check if running in auto mode (allow automation scripts to bypass prompts)
AUTO_MODE="${AUTO_START_MODE:-0}"

# Create necessary directories
mkdir -p "$LOG_DIR" "$OUTPUT_DIR" "data/raw/hsp/phase3"

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

# Check for environment variables (attempt to source .env when missing)
if [ -z "$HSP_EMAIL" ] && [ -z "$HSP_USERNAME" ]; then
    if [ -f ".env" ]; then
        set -a
        # shellcheck disable=SC1091
        source .env
        set +a
    fi

    if [ -z "$HSP_EMAIL" ] && [ -z "$HSP_USERNAME" ]; then
        if [ "$AUTO_MODE" = "1" ]; then
            echo "⚠️  Warning: HSP_EMAIL or HSP_USERNAME not set, but continuing in auto mode"
        else
            echo "⚠️  Warning: HSP_EMAIL or HSP_USERNAME not set"
            echo "   Make sure .env file exists or export environment variables"
            read -p "Continue anyway? (y/N) " -n 1 -r
            echo
            if [[ ! $REPLY =~ ^[Yy]$ ]]; then
                exit 1
            fi
        fi
    fi
fi

# Function to check if process is running
check_process() {
    local pid_file="$1"
    if [ -f "$pid_file" ]; then
        local pid
        pid=$(cat "$pid_file")
        if ps -p "$pid" > /dev/null 2>&1; then
            return 0
        else
            rm -f "$pid_file"
            return 1
        fi
    fi
    return 1
}

# Check if already running (pid tied to this invocation)
if check_process "$PID_FILE"; then
    echo "⚠️  Process already running (PID: $(cat "$PID_FILE"))"
    echo "   Log file: $LOG_FILE"
    exit 1
fi

# Check for other phase3 processes
EXISTING_PID=$(ls -t "$LOG_DIR"/phase3_batch_*.pid 2>/dev/null | head -1)
if [ -n "$EXISTING_PID" ] && check_process "$EXISTING_PID"; then
    if [ "$AUTO_MODE" = "1" ]; then
        echo "⚠️  Another Phase 3 process is already running, but continuing in auto mode"
        echo "   PID file: $EXISTING_PID"
        echo "   PID: $(cat "$EXISTING_PID")"
    else
        echo "⚠️  Another Phase 3 process is already running:"
        echo "   PID file: $EXISTING_PID"
        echo "   PID: $(cat "$EXISTING_PID")"
        read -p "Start new process anyway? (y/N) " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            exit 1
        fi
    fi
fi

# Calculate estimated time
# 61 days / 7 days per chunk = ~9 chunks per day type
# 3 day types (WEEKDAY, SATURDAY, SUNDAY) = 27 chunks per route
# 10 routes = 270 total chunks
# Each chunk: ~3-4 seconds (request + 1-3s delay)
# Total: ~270 chunks × 4s ≈ 18 minutes (minimum)
# With processing overhead: ~1.5-2.5 hours estimated
echo "📊 Phase 3 Collection Estimate:"
echo "   Date Range: 2025-03-01 to 2025-04-30 (61 days)"
echo "   Routes: 10"
echo "   Day Types: WEEKDAY, SATURDAY, SUNDAY (3 types)"
echo "   Date Chunks: ~9 chunks per day type (≤7 days each)"
echo "   Total Chunks: ~270 chunks"
echo "   Request Interval: 1-3 seconds"
echo "   Estimated Time: 1.5-2.5 hours"
echo ""

# Start background process
echo "🚀 Starting Phase 3 batch collection in background..."
echo "   Config: $CONFIG_FILE"
echo "   Log file: $LOG_FILE"
echo "   PID file: $PID_FILE"
echo "   Status file: $STATUS_FILE"
echo ""

# Initialize status file
echo "{\"started_at\": \"$(date -u +"%Y-%m-%dT%H:%M:%SZ")\", \"status\": \"starting\", \"chunks_completed\": 0, \"routes_completed\": 0}" > "$STATUS_FILE"

# Run in background with nohup and unbuffered output
PYTHONUNBUFFERED=1 nohup python3 -u "$SCRIPT_DIR/fetch_hsp_batch.py" "$CONFIG_FILE" --phase "PHASE3" >> "$LOG_FILE" 2>&1 &
PID=$!

# Save PID
echo "$PID" > "$PID_FILE"

# Wait a moment to verify start
sleep 3

if ps -p "$PID" > /dev/null 2>&1; then
    echo "✅ Phase 3 process started successfully!"
    echo "   PID: $PID"
    echo "   Log file: $LOG_FILE"
    echo "   PID file: $PID_FILE"
    echo "   Status file: $STATUS_FILE"
    echo ""
    echo "📋 Useful commands:"
    echo "   View logs: tail -f $LOG_FILE"
    echo "   Check status: ./check_phase3.sh"
    echo "   Stop process: ./stop_phase3.sh"
    echo "   Monitor progress: watch -n 10 './check_phase3.sh'"
    echo ""
    echo "💡 The process will:"
    echo "   - Split date range into ≤7 day chunks"
    echo "   - Wait 1-3 seconds between each request"
    echo "   - Process all 10 routes sequentially"
    echo "   - Skip previously completed tasks automatically"
else
    echo "❌ Process failed to start. Check log file: $LOG_FILE"
    rm -f "$PID_FILE" "$STATUS_FILE"
    exit 1
fi



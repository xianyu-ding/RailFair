#!/bin/bash
# Check status of Phase 2 batch collection
# Usage: ./check_phase2.sh [pid_file]

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

LOG_DIR="logs"
DATA_DIR="data"

# If PID file provided, use it; otherwise find latest
if [ -n "$1" ]; then
    PID_FILE="$1"
else
    # Find latest PID file
    PID_FILE=$(ls -t "$LOG_DIR"/phase2_batch_*.pid 2>/dev/null | head -1)
fi

if [ -z "$PID_FILE" ] || [ ! -f "$PID_FILE" ]; then
    echo "❌ No Phase 2 PID file found. Process may not be running."
    echo ""
    echo "💡 To start Phase 2 collection:"
    echo "   ./run_phase2_background.sh"
    exit 1
fi

PID=$(cat "$PID_FILE")
TIMESTAMP=$(basename "$PID_FILE" .pid | sed 's/phase2_batch_//')
LOG_FILE="${LOG_DIR}/phase2_batch_${TIMESTAMP}.log"
STATUS_FILE="${LOG_DIR}/phase2_batch_${TIMESTAMP}.status"
PROGRESS_FILE="${DATA_DIR}/progress_phase2.json"
DB_FILE="${DATA_DIR}/railfair.db"

echo "📊 Phase 2 Batch Collection Status"
echo "==================================="
echo "PID: $PID"
echo "Log file: $LOG_FILE"
echo ""

# Check if process is running
if ps -p "$PID" > /dev/null 2>&1; then
    echo "✅ Process is RUNNING"
    echo ""
    
    # Process info
    echo "📈 Process Info:"
    ps -p "$PID" -o pid,ppid,etime,pcpu,pmem,cmd | head -2
    echo ""
    
    # Calculate elapsed time
    START_TIME=$(ps -p "$PID" -o lstart= | xargs)
    if [ -n "$START_TIME" ]; then
        ELAPSED=$(ps -p "$PID" -o etime= | xargs)
        echo "⏱️  Running time: $ELAPSED"
    fi
    echo ""
    
    # Check progress file
    if [ -f "$PROGRESS_FILE" ]; then
        echo "📊 Progress Summary:"
        if command -v python3 > /dev/null 2>&1; then
            python3 << EOF
import json
import sys
from datetime import datetime

try:
    with open("$PROGRESS_FILE", 'r') as f:
        progress = json.load(f)
    
    completed = len(progress.get('completed_routes', []))
    failed = len(progress.get('failed_routes', []))
    total_records = progress.get('total_records', 0)
    started_at = progress.get('started_at')
    last_updated = progress.get('last_updated')
    
    print(f"   Completed routes: {completed}/10")
    print(f"   Failed routes: {failed}")
    print(f"   Total records: {total_records}")
    
    if started_at:
        print(f"   Started: {started_at}")
    if last_updated:
        print(f"   Last updated: {last_updated}")
    
    if completed > 0:
        print(f"\n   ✅ Completed routes:")
        for route in progress.get('completed_routes', [])[:5]:
            print(f"      - {route}")
        if completed > 5:
            print(f"      ... and {completed - 5} more")
    
    if failed > 0:
        print(f"\n   ❌ Failed routes:")
        for route_info in progress.get('failed_routes', [])[:3]:
            route_name = route_info.get('route', 'Unknown')
            error = route_info.get('error', 'Unknown error')
            print(f"      - {route_name}: {error[:60]}...")
        
except Exception as e:
    print(f"   Error reading progress: {e}")
EOF
        else
            echo "   (Install python3 to see detailed progress)"
        fi
    else
        echo "   Progress file not found yet (may be starting)"
    fi
    echo ""
    
    # Database stats
    if [ -f "$DB_FILE" ]; then
        echo "💾 Database Stats:"
        if command -v sqlite3 > /dev/null 2>&1; then
            METRICS_COUNT=$(sqlite3 "$DB_FILE" "SELECT COUNT(*) FROM hsp_service_metrics;" 2>/dev/null || echo "N/A")
            DETAILS_COUNT=$(sqlite3 "$DB_FILE" "SELECT COUNT(*) FROM hsp_service_details;" 2>/dev/null || echo "N/A")
            echo "   Service Metrics: $METRICS_COUNT records"
            echo "   Service Details: $DETAILS_COUNT records"
        else
            echo "   (Install sqlite3 to see database stats)"
        fi
    fi
    echo ""
    
    # Recent log output
    echo "📝 Last 15 lines of log:"
    echo "---"
    if [ -f "$LOG_FILE" ]; then
        tail -n 15 "$LOG_FILE"
    else
        echo "Log file not found yet"
    fi
    
else
    echo "❌ Process is NOT RUNNING"
    echo ""
    
    # Check if it completed successfully
    if [ -f "$LOG_FILE" ]; then
        echo "📝 Last 20 lines of log:"
        echo "---"
        tail -n 20 "$LOG_FILE"
        echo ""
        
        # Check for completion message
        if grep -q "COLLECTION SUMMARY" "$LOG_FILE"; then
            echo "✅ Process appears to have completed. Check log for summary."
        elif grep -q "Fatal error\|Error\|Exception" "$LOG_FILE"; then
            echo "⚠️  Process may have encountered an error. Check log above."
        fi
    fi
    
    echo ""
    echo "💡 You may want to remove the PID file: rm $PID_FILE"
fi

